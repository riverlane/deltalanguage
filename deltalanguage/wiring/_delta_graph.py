"""Module for defining a DeltaGraph, this is a collection of connected
nodes and placeholders.
"""

from __future__ import annotations
from collections import deque, OrderedDict
from copy import deepcopy
from typing import TYPE_CHECKING, Deque, Dict, List, Set, Tuple, Type, Union
import logging
import textwrap

import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

from deltalanguage.data_types import make_forked_return
from deltalanguage.logging import make_logger
from ..data_types import (BaseDeltaType,
                          DeltaIOError,
                          DeltaTypeError,
                          DUnion,
                          Top)
from ._node_classes.abstract_node import AbstractNode
from ._node_classes.node_bodies import Latency
from ._node_classes.real_nodes import OutPort, PyConstNode
from ._node_classes.splitter_nodes import PySplitterNode
from ._node_factories import py_node_factory

if TYPE_CHECKING:
    from ._node_classes.placeholder_node import PlaceholderNode
    from ._node_classes.real_nodes import RealNode


class DeltaGraph:
    """A collection of nodes and placeholders that make up a single DeltaGraph.

    Also responsible for statically controlling a stack of active graphs
    and naming placeholders.

    Parameters
    ----------
    name : str
        Graph's name.

    lvl : int
        The level at which logs are displayed.
        These are the same levels as in Python's :py:mod:`logging` package.
        By default only error logs are displayed.

    Examples
    --------
    Graph definition starts with defining individual nodes (or importing them
    from a library). Most importantly there must be a node that formally ends
    the evaluation of the graph by calling
    :py:class:`DeltaRuntimeExit<deltalanguage.runtime.DeltaRuntimeExit>`.
    Here is a node like this, it prints an incoming integer and
    calls for exit:

    .. code-block:: python

        >>> from deltalanguage.data_types import NoMessage
        >>> from deltalanguage.runtime import DeltaRuntimeExit
        >>> from deltalanguage.wiring import DeltaBlock

        >>> @DeltaBlock(allow_const=False)
        ... def print_and_exit(a: int) -> NoMessage:
        ...     print(a)
        ...     raise DeltaRuntimeExit

    The graph definition uses python's ``with`` statement where one simply
    wires up outputs of nodes with inputs of the other nodes:

    .. code-block:: python

        >>> with DeltaGraph() as graph:
        ...     print_and_exit(42) # doctest:+ELLIPSIS
        print_and_exit...

    Simply print the graph to see its content:

    .. code-block:: python

        print(graph)

    Note that this graph has 2 nodes, as a dummy node has been created for
    a constant.
    Also note that the name of each node has its index appended in the end:    

    One can also use the interface with ``matplotlib`` to draw
    the same graph:

    .. code-block:: python

        graph.draw()

    In order to evaluate the graph it should be run by a runtime. The Deltaflow
    language comes with a simple runtime
    :py:class:`DeltaPySimulator<deltalanguage.runtime.DeltaPySimulator>`:

    .. code-block:: python

        >>> from deltalanguage.runtime import DeltaPySimulator

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        42

    Node inputs and outputs must be typed (in case of no output
    :py:class:`NoMessage<deltalanguage.data_types.NoMessage>` is used as above).
    To check the correctness of wiring manually one can call this method:

    .. code-block:: python

        >>> graph.check()
        True

    Attributes
    ----------
    global_stack : list
        Store of active graphs, used as a stack.
    placeholder_name_index : int
        Used to ensure that every placeholder node in the graph has a unique
        name.
    """

    global_stack = []
    placeholder_name_index: int = 0

    def __init__(self, name=None, lvl: int = logging.ERROR):
        self.name = name
        self.placeholders: Dict[str, PlaceholderNode] = {}
        self.nodes: List[RealNode] = []
        self.log = make_logger(lvl, "DeltaGraph")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if name is None:
            self._name = "main"
        else:
            self._name = name

    def __enter__(self):
        """Creation of the graph context, sets this graph as the active graph
        at the top of the graph stack.
        """
        DeltaGraph.global_stack.append(self)
        return self

    def __exit__(self, *args):
        """End of the graph context, pops from top of graph stack as this
        graph is no longer active.
        """
        DeltaGraph.global_stack.pop()

    def __str__(self) -> str:
        ret = f"DeltaGraph[{self.name}] {{\n"
        ret += textwrap.indent(''.join(map(str, self.nodes)), prefix='    ')
        ret += "}\n"

        if self.placeholders:
            ret += f"There are placeholders!\n{self.placeholders.keys()}.\n"

        return ret

    def __repr__(self) -> str:
        return str(self)

    def flatten(self, other):
        """Graphs can be declared in different scopes but we want to then
        merge them and use them in one graph.
        To do this, connected graphs must be merged into one graph containing
        a list of all the nodes across all original graphs.
        This function is called when an out-port is added to a node where
        the destination graph is different from the origin graph.

        Parameters
        ----------
        other : DeltaGraph
            The other graph that must be merged into this one
        """
        # Merge node lists and set alien nodes graph to be this graph
        alien_nodes = other.nodes
        for alien_node in alien_nodes:
            self.nodes.append(alien_node)
            alien_node.graph = self

        # Merge placeholder dicts
        self.placeholders.update(other.placeholders)

    def _merge_out_ports(self, out_ports):
        """Merge a list of out ports into a single out-port, creating a
        splitter node as required. Needed when the same out-port appears
        multiple times on the same node.

        Parameters
        ----------
        out_ports : List[OutPort]

        Returns
        -------
        OutPort
            Single merged out port that outputs to splitter that then
            outputs to all original destinations.
        """
        if len(out_ports) == 1:
            return out_ports[0]

        elif len(out_ports) > 1:
            # name type and node should be the same across all given out-ports
            merged_name = out_ports[0].port_name
            merged_type = out_ports[0].port_type
            merged_node = out_ports[0].node
            for out_port in out_ports[1:]:
                if out_port.port_name != merged_name:
                    raise ValueError(f"Merged out-port names " +
                                     f"{str(merged_name)} and " +
                                     f"{str(out_port.port_name)} " +
                                     f"do not match.")
                if out_port.port_type != merged_type:
                    raise ValueError(f"Merged out-port types " +
                                     f"{str(merged_type)} and " +
                                     f"{str(out_port.port_type)} " +
                                     f"do not match.")
                if out_port.node != merged_node:
                    raise ValueError(f"Merged out-port node " +
                                     f"{str(merged_node)} and " +
                                     f"{str(out_port.node)}" +
                                     f"do not match.")
            all_destinations = [x.destination for x in out_ports]

            # create a body of the splitter node
            _reps = len(all_destinations)
            _SplitterT, _SplitterC = make_forked_return(
                {'out' + str(i): merged_type for i in range(_reps)}
            )

            def _splitter(to_split: merged_type) -> _SplitterT:
                return _SplitterC(*(deepcopy(to_split) for _ in range(_reps)))

            # If merged_node has forked output only get the relevant argument
            # TODO This duplicates PyConstBody.eval and should be refactored
            if out_ports[0].index is None:
                merged_node_output = merged_node
            else:
                merged_node_output = getattr(merged_node, out_ports[0].index)

            # create a const splitter node if merged_node is const
            new_node = py_node_factory(
                self,
                isinstance(merged_node, PyConstNode),
                _splitter,
                OrderedDict([('to_split', merged_type)]),
                _SplitterT,
                merged_node_output,
                name='splitter',
                latency=Latency(time=100),
                lvl=merged_node.log.level
            )

            # send splitters outputs to the original destinations
            for i, dest in enumerate(all_destinations):
                new_node.add_out_port(dest, 'out' + str(i))

            # get in port of the splitter
            _in_port_name = list(new_node.in_ports.keys())[0]
            merged_destination = new_node.in_ports[_in_port_name]

            # return a new out port instead of original out_ports
            return OutPort(merged_name,
                           merged_type,
                           merged_destination,
                           merged_node)

        else:
            return None  # An empty list has been given so return None

    def do_automatic_splitting(self):
        """You cannot have multiple out-ports for the same piece of data in
        Deltaflow.
        Instead you have a single wire to a splitter node which outputs several
        separate wires.
        This code will automatically add splitter nodes to this graph
        where needed.
        """
        # For each node, group out-ports by their name in a dict
        for node in self.nodes:
            out_ports_dict: Dict[str, List[OutPort]] = {}
            for x in node.out_ports:
                if x.port_name in out_ports_dict:
                    out_ports_dict[x.port_name].append(x)
                else:
                    out_ports_dict[x.port_name] = [x]

            # Set this nodes out ports to a list of merged out ports
            node.out_ports = [self._merge_out_ports(x)
                              for x in out_ports_dict.values()]

    def check(self):
        """Check that the graph is correct.

        This is a 2-stage process that is outlined below:

            1. Check nodes and wires (data streams):

                - Nodes names are unique.
                - I/O-ports are unique
                - All non-optional inputs are provided. If an optional input is
                  not provided or output does not go anywhere then it is fine.

            2. Check typing of wires, see the impl and characterization tests.

        Returns
        -------
        bool
            ``True`` if correct.

        .. todo::
            Add extra checks of splitting/forking of wires in step 1.
        """
        # check node names
        nodes_names = [node.name for node in self.nodes]
        if len(set(nodes_names)) != len(nodes_names):
            raise DeltaIOError(f"nodes' names should be unique\n"
                               f"graph={self}")

        # check ports
        in_ports_all = [port
                        for node in self.nodes
                        for port in node.in_ports.values()]
        out_ports_all = [port
                         for node in self.nodes
                         for port in node.out_ports]
        out_ports_dest = [port.destination
                          for node in self.nodes
                          for port in node.out_ports]
        if len(set(in_ports_all)) != len(in_ports_all):
            raise DeltaIOError(f"in_ports should be unique\n"
                               f"graph={self}")
        if len(set(out_ports_all)) != len(out_ports_all):
            raise DeltaIOError(f"out_ports should be unique\n"
                               f"graph={self}")
        if len(set(out_ports_dest)) != len(out_ports_dest):
            raise DeltaIOError(f"out_ports destianations should be unique\n"
                               f"graph={self}")

        # check port names
        # note: out_ports_names can be not unique
        in_ports_names = [port.port_name for port in in_ports_all]
        out_ports_dest_names = [port.port_name for port in out_ports_dest]
        if len(set(in_ports_names)) != len(in_ports_names):
            raise DeltaIOError(f"in_ports' names should be unique\n"
                               f"graph={self}")
        if len(set(out_ports_dest_names)) != len(out_ports_dest_names):
            raise DeltaIOError(f"out_ports' destination names should be unique\n"
                               f"graph={self}")

        # TODO check that if splitting is needed then out_port' names are
        # unique, otherwise raise DeltaIOError

        # check missing inputs
        in_ports_unused = [port
                           for node in self.nodes
                           for port in node.in_ports.values()
                           if not port in out_ports_dest]
        for port in in_ports_unused:
            if not port.is_optional:
                raise DeltaIOError(f"Mandatory input is not provided\n"
                                   f"graph={self}\n{port=}")

        # check each channel typing
        for port in out_ports_all:
            try:
                self.check_wire(type_s=port.port_type,
                                type_r=port.destination.port_type)
            except DeltaTypeError as port_type_err:
                raise DeltaTypeError(
                    port_type_err.args[0] + f'\n{port=}') from port_type_err

        return True

    @staticmethod
    def check_wire(type_s: BaseDeltaType, type_r: BaseDeltaType):
        """Check that ``type_s`` sent by :py:class:`OutPort` can by received
        as ``type_r`` by :py:class:`InPort`.

        In case when ``type_s`` is an instance of
        :py:class:`DUnion<deltalanguage.data_types.DUnion>`, it is
        enforces that each each type is received, i.e. strict typing.

        Returns
        -------
        bool
            ``True`` if okay.

        Examples
        --------
        Unit tests of this method characterise the behaviour.

        .. warning::

            Deltaflow data types implemented as class instances with defined
            size. In order to compare 2 types types use `__eq__` method.

        """
        if (not isinstance(type_s, BaseDeltaType)) \
                or (not isinstance(type_r, BaseDeltaType)):
            raise DeltaTypeError(f"Unsupported types\n{type_s=}\n{type_r=}")

        if type_r == type_s:
            return True

        if type_r == Top():
            return True

        if type(type_r) == DUnion and Top() in type_r.elems:
            return True

        raise DeltaTypeError(f"Broken strict typing\n"
                             f"{type_s=}\n{type_r=}")

    def find_node_by_name(self, name: str):
        """Get the node(s) with the given name from the graph.

        Parameters
        ----------
        name : str
            Name of node to return

        Returns
        -------
        Node or list of nodes matching this name.
        """
        nodes = []
        for node in self.nodes:
            if not node.name.split('_')[-1].isdigit():
                raise ValueError(f'Node {node.name} has a strange name')

            if '_'.join(node.name.split('_')[:-1]) == name:
                nodes.append(node)

        if len(nodes) == 0:
            return None
        elif len(nodes) == 1:
            return nodes[0]
        else:
            return nodes

    def add_node(self, node: RealNode):
        """Add a node to this graph.

        Parameters
        ----------
        node : RealNode
        """
        self.nodes.append(node)

    def add_placeholder(self, key: str, placeholder: PlaceholderNode):
        """Add a placeholder with unique key to this graph.

        Parameters
        ----------
        key : str
            Key to add placeholder at.
        placeholder : PlaceholderNode
            Placeholder node to add.
        """
        if key in self.placeholders.keys():
            raise KeyError(
                f"Placeholder with name {key} already exists in current graph."
            )
        else:
            self.placeholders[key] = placeholder

    def get_networkx_graph(self, port_nodes: bool = False):
        """Construct NetworkX representation of graph.

        Parameters
        ----------
        port_nodes : bool = False
            If ``True``, ports are presented as types of nodes in the graph.
            If ``False``, port details are added as extra labels to edges.

        Returns
        -------
        nx.MultiDiGraph
            Directional multigraph object used for graphical representation of
            :py:class:`DeltaGraph`.
        """
        graph = nx.MultiDiGraph()
        for node in self.nodes:
            graph.add_node(node.name, name=node.name, type="block")
            for out_port in node.out_ports:
                if port_nodes:
                    # If output is forked, add node for out_port
                    # Else simply use main node
                    if out_port.index:
                        src = f"out_{str(out_port.port_name)}"
                        graph.add_node(src,
                                       name=out_port.index,
                                       type="out_port")
                        graph.add_edge(node.name, src)
                    else:
                        src = node.name
                    dest = f"in_{str(out_port.dest_port_name)}"
                    graph.add_node(dest,
                                   name=out_port.dest_port_index,
                                   type="in_port")
                    graph.add_edge(dest, out_port.dest_node_name)
                    graph.add_edge(src, dest, type=str(out_port.port_type))
                else:
                    if out_port.index:
                        src = out_port.index
                    else:
                        src = ""
                    dest = out_port.dest_port_index
                    graph.add_edge(node.name,
                                   out_port.dest_node_name,
                                   src=src,
                                   type=str(out_port.port_type),
                                   dest=dest)

        return graph

    def draw(self, seed: int = None, iterations: int = 50, **kwargs):
        """Draw the graph using NetworkX's default drawing tool.
        Additional parameters are passed to draw_networkx.
        See the NetworkX documentation for further details on parameters.
        """
        if seed is None:
            seed = np.random

        graph = self.get_networkx_graph()
        pos = nx.spring_layout(graph, seed=seed, iterations=iterations)

        # Check to see if there are duplicate edges
        if any([key >= 1 for (_, _, key) in graph.edges]):
            self.log.warning("Where multiple outputs from one node go to" +
                             "the same node, only one edge is visible")

        # Make figure size scale with node number
        fig_len = max(4, round(graph.number_of_nodes()/2))
        plt.figure(figsize=(round(fig_len*1.5), fig_len))

        # Add labels as matplotlib text objects
        for name, loc in pos.items():
            plt.text(loc[0], loc[1], name,
                     horizontalalignment='center', verticalalignment='center')

        plt.axis('off')
        nx.draw_networkx(graph, pos=pos, with_labels=False,
                         connectionstyle='arc3, rad = 0.1', **kwargs)

    def write_gml(self, path, **kwargs):
        """Write graph visualisation as a GraphML file.

        Notes
        -----
        With this file, we can now import the graph into a program such as
        [Cytoscape](https://cytoscape.org/). After importing the graph,
        Cytoscape allows us to apply a layout algorithm to this graph,
        or let it use the one it finds most suitable. We can also control
        the style of the graph, and modify the appearance of nodes and edges,
        including different styles for ports and nodes. An example style
        for Deltaflow graphs is given in `deltalanguage/DeltaStyle.xml`.

        After calling this method, with a path pointing to an empty .gml
        file, install and open Cytoscape. 
        Select your .gml file from the import dialog via:
        File > Import > Network from file
        Ensure the 'Network' panel is selected on the left toolbar, in which 
        you can select which network/graph you are visualising.
        To import a style select your .xml file via:
        File > Import > Style from file
        Along the left toolbar, select the 'Style' panel.
        In this panel there is a drop-down menu that allows you to pick 
        which style you are editing or using to visualise graphs.
        To spread nodes out, you can apply a layout function.
        Layout -> Edge-weighted Spring Embedded Layout -> (none)
        """
        nx.write_gml(self.get_networkx_graph(**kwargs), path)

    @classmethod
    def get_next_placeholder_name(cls) -> str:
        """Class method to get a new, globally unique, placeholder name.

        Returns
        -------
        str
        """
        ret_val = "placeholder_" + str(cls.placeholder_name_index)
        cls.placeholder_name_index += 1
        return ret_val

    @classmethod
    def stack(cls):
        """Returns the graph stack."""
        return cls.global_stack

    @classmethod
    def current_graph(cls):
        """Returns the active graph at the top of the graph stack."""
        return cls.global_stack[-1]

    @classmethod
    def clean_stack(cls):
        """Fresh start the stack.

        This is useful for tests where a fresh start is needed.
        """
        cls.global_stack = []
        cls.placeholder_name_index = 0
        AbstractNode.reset_index()


def _get_neighbours_of_type(
        this_node: RealNode,
        types: Union[Type[RealNode], Tuple[Type[RealNode], ...]]
) -> List[RealNode]:
    """Checks all destination nodes of ``this_node`` and returns a list of
    those that are in ``types``.
    """
    return [port.destination.node
            for port in this_node.out_ports
            if isinstance(port.destination.node, types)]


def is_needed(source_node: RealNode,
              useful_node_cls: Tuple[Type[RealNode], ...],
              forwarding_node_cls: Type[RealNode] = PySplitterNode) -> bool:
    """Determine if ``source_node`` needs to run.

    If a single node of ``useful_node_cls`` is found return ``True``,
    otherwise ``False``.

    The current condition of search:
    - check if any of destination nodes is in ``useful_node_cls``
    - if any of destination nodes is in ``forwarding_node_cls``, use them
      to search for its destination nodes

    Parameters
    ----------
    source_node : RealNode
        Node which maybe needs to run.
    useful_node_cls : Tuple[Type[RealNode], ...]
        If one of these node types is in the destination tree, then the source
        is useful -> returns True.
        Otherwise the result is False.
    forwarding_node_cls : Type[RealNode]
        Type or tuple of types of nodes through which paths should be followed.
    """
    node_queue: Deque[RealNode] = deque()
    visited_nodes: Set[RealNode] = set()
    node_queue.append(source_node)

    while node_queue:
        node = node_queue.popleft()
        visited_nodes.add(node)
        if _get_neighbours_of_type(node, useful_node_cls):
            return True
        forwarding_dests = _get_neighbours_of_type(node, forwarding_node_cls)
        node_queue.extend([node for node in forwarding_dests
                           if node not in visited_nodes])

    return False
