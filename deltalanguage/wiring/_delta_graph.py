"""Module for defining a DeltaGraph, this is a collection of connected
nodes and placeholders.
"""

from __future__ import annotations
from copy import deepcopy
import inspect
from typing import TYPE_CHECKING, Dict, List, Union, OrderedDict
import logging
import textwrap
import sys
import dill

import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

from deltalanguage.logging import make_logger
from ..data_types import (BaseDeltaType,
                          DeltaIOError,
                          DeltaTypeError,
                          Optional,
                          Top)
from ._node_classes.abstract_node import AbstractNode
from ._node_classes.node_bodies import (Latency,
                                        PyConstBody,
                                        PyFuncBody,
                                        PyMethodBody,
                                        PythonBody,
                                        PyInteractiveBody)
from ._node_classes.real_nodes import (PythonNode,
                                       OutPort,
                                       as_node)
from ._node_templates import NodeTemplate

if TYPE_CHECKING:
    from ._node_classes.placeholder_node import PlaceholderNode
    from ._node_classes.real_nodes import RealNode
    import capnp


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
        These are the same levels as in Python's ``logging`` package.
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

        >>> import deltalanguage as dl

        >>> @dl.DeltaBlock(allow_const=False)
        ... def print_and_exit(a: int) -> dl.Void:
        ...     print(a)
        ...     raise dl.DeltaRuntimeExit

    The graph definition uses python's ``with`` statement where one simply
    wires up outputs of nodes with inputs of the other nodes:

    .. code-block:: python

        >>> with dl.DeltaGraph() as graph:
        ...     print_and_exit(42)

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

    In order to evaluate the graph it should be executed on a runtime simulator
    or a runtime.
    The Deltaflow language comes with a simple runtime simulator
    :py:class:`DeltaPySimulator<deltalanguage.runtime.DeltaPySimulator>`:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> dl.DeltaPySimulator(graph).run()
        42

    Node inputs and outputs must be typed (in case of no output no
    annotation or `outputs` is needed).
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

    def __init__(self, name: str = "main", lvl: int = logging.ERROR):
        self.name = name
        self.placeholders: Dict[str, PlaceholderNode] = {}
        self.nodes: List[RealNode] = []
        self.log = make_logger(lvl, "DeltaGraph")
        # used below to silent doctest unwanted outputs
        self._org_displayhook = None

    def __eq__(self, other) -> bool:
        """Equality, up to isomorphism via .df file.
        """

        def get_networkx_iso_graph(d_graph):
            """Create a modified networkx graph that has enough information in to 
            evaluated isomorphism between DeltaGraphs.
            """
            graph = nx.MultiDiGraph()
            for node in d_graph.nodes:
                graph.add_node(node.full_name,
                               name=node.name,
                               inputs=node.inputs,
                               outputs=node.outputs,
                               in_ports=node.in_ports,
                               out_ports=node.out_ports,
                               bodies=node.bodies)
                for out_port in node.out_ports:
                    src = out_port.index
                    dest = out_port.destination.index
                    graph.add_edge(node.full_name,
                                   out_port.dest_node_name,
                                   key=(src, dest))

            return graph

        def netx_edge_match(e1, e2):
            """Edges get given as dict of key to edge data. We have no 
            interesting edge data as it is stored in the ports.
            So all the data we need to compare is in the key.
            """
            return e1.keys() == e1.keys()

        def netx_node_match(n1, n2):
            if n1['name'] != n2['name']:
                return False

            if n1['inputs'] != n2['inputs']:
                return False

            if n1['outputs'] != n2['outputs']:
                return False

            if n1['in_ports'] != n2['in_ports']:
                return False

            if n1['out_ports'] != n2['out_ports']:
                return False

            return n1['bodies'] == n2['bodies']

        if not isinstance(other, DeltaGraph):
            return False

        if self.name != other.name:
            return False

        if self.placeholders != other.placeholders:
            return False

        g1 = get_networkx_iso_graph(self)
        g2 = get_networkx_iso_graph(other)
        return nx.algorithms.is_isomorphic(g1, g2,
                                           node_match=netx_node_match,
                                           edge_match=netx_edge_match)

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
        if 'doctest' in sys.modules:
            self._org_displayhook = sys.displayhook
            sys.displayhook = lambda x: None

        DeltaGraph.global_stack.append(self)
        return self

    def __exit__(self, *args):
        """End of the graph context, pops from top of graph stack as this
        graph is no longer active.
        """
        if not self.select_bodies(override=False):
            self.log.info(f'Graph {self.name} contains a node without a body, '
                          'please define it before execution.')

        self.do_automatic_splitting()
        DeltaGraph.global_stack.pop()

        if 'doctest' in sys.modules:
            sys.displayhook = self._org_displayhook

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
            merged_index = out_ports[0].index
            merged_type = out_ports[0].port_type
            merged_node = out_ports[0].node
            for out_port in out_ports[1:]:
                if out_port.index != merged_index:
                    raise ValueError("Merged out-port names " +
                                     f"{str(merged_index)} and " +
                                     f"{str(out_port.index)} " +
                                     "do not match.")
                if out_port.port_type != merged_type:
                    raise ValueError("Merged out-port types " +
                                     f"{str(merged_type)} and " +
                                     f"{str(out_port.port_type)} " +
                                     "do not match.")
                if out_port.node != merged_node:
                    raise ValueError("Merged out-port node " +
                                     f"{str(merged_node)} and " +
                                     f"{str(out_port.node)}" +
                                     "do not match.")
            all_destinations = [x.destination for x in out_ports]

            # create a body of the splitter node
            _reps = len(all_destinations)
            outputs = [('out' + str(i), merged_type) for i in range(_reps)]

            def _splitter(to_split: merged_type):
                return tuple(deepcopy(to_split) for _ in range(_reps))

            # Dynamically annotated function does not get signature set
            # properly, so to use normal interface we have to manually set it
            params = [inspect.Parameter('to_split',
                                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                        annotation=merged_type)]
            _splitter.__signature__ = inspect.Signature(parameters=params)

            # Get the relevant part of the output
            merged_node_output = getattr(merged_node, out_ports[0].index)

            # Construct the node using NodeTemplate
            template = NodeTemplate.merge_deltablock(None,
                                                     outputs,
                                                     _splitter,
                                                     merged_node.is_const(),
                                                     name='splitter',
                                                     latency=Latency(time=100),
                                                     lvl=merged_node.log.level)
            new_node = template.call_with_graph(self, merged_node_output)

            # send splitters outputs to the original destinations
            for i, dest in enumerate(all_destinations):
                new_node.add_out_port(dest, 'out' + str(i))

            # get in port of the splitter
            merged_destination = new_node.in_ports[0]

            # return a new out port instead of original out_ports
            return OutPort(merged_index,
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
                if x.name in out_ports_dict:
                    out_ports_dict[x.name].append(x)
                else:
                    out_ports_dict[x.name] = [x]

            # Set this nodes out ports to a list of merged out ports
            node.out_ports = [self._merge_out_ports(x)
                              for x in out_ports_dict.values()]

    def check(self, allow_top: bool = True, allow_node_key: bool = True):
        """Check that the graph is correct.

        This is a 2-stage process that is outlined below:

            1. Check nodes and wires (data streams):

                - Nodes names are unique.
                - I/O-ports are unique
                - All non-optional inputs are provided. If an optional input is
                  not provided or output does not go anywhere then it is fine.

            2. Check typing of wires, see the impl and characterization tests.

        Parameters
        ----------
        allow_top : bool
            Whether or not input ports are allowed to have type Top().
        allow_node_key : bool
            Whether or not nodes are allowed to have a node key
            (a debugging parameter from which node bodies can send/receive
            messages).

        Returns
        -------
        bool
            ``True`` if correct.


        .. todo::
            Add extra checks of splitting/multi-output of wires in step 1.
        """
        # check node names
        nodes_names = [node.full_name for node in self.nodes]
        if len(set(nodes_names)) != len(nodes_names):
            raise DeltaIOError(f"nodes' names should be unique\n"
                               f"graph={self}")

        # check ports
        in_ports_all = [port
                        for node in self.nodes
                        for port in node.in_ports]
        out_ports_all = [port
                         for node in self.nodes
                         for port in node.out_ports]
        out_ports_dest = [port.destination
                          for node in self.nodes
                          for port in node.out_ports]

        # port name uniqueness guarantees port object uniqueness
        in_ports_names = [port.name for port in in_ports_all]
        out_ports_names = [port.name for port in out_ports_all]
        out_ports_dest_names = [port.name for port in out_ports_dest]
        if len(set(in_ports_names)) != len(in_ports_names):
            raise DeltaIOError(f"in_ports' names should be unique\n"
                               f"graph={self}")
        if len(set(out_ports_names)) != len(out_ports_names):
            raise DeltaIOError(f"out_ports' names should be unique\n"
                               f"graph={self}")
        if len(set(out_ports_dest_names)) != len(out_ports_dest_names):
            raise DeltaIOError(f"out_ports' destination names should be unique\n"
                               f"graph={self}")

        # nodes with interactive bodies cannot be portless,
        # as they block simulation, until scheduling is implemented
        for node in self.nodes:
            if not allow_node_key and node.node_key is not None:
                raise DeltaIOError(
                    "Node has a node key when allow_node_key is set to False")
            for body in node.bodies:
                if (isinstance(body, PyInteractiveBody)
                        and len(node.in_ports) == 0
                        and len(node.out_ports) == 0):
                    raise DeltaIOError(
                        f"Node {node} without any I/O has an interactive body "
                        f"{body}. At the moment this is not supported.\n"
                        "Please either remove this body or connect this node "
                        "to another one."
                    )

        # check missing inputs
        in_ports_unused = [port
                           for node in self.nodes
                           for port in node.in_ports
                           if not port in out_ports_dest]
        for port in in_ports_unused:
            if not port.is_optional:
                raise DeltaIOError(f"Mandatory input is not provided\n"
                                   f"graph={self}\n{port=}")

        # check each channel typing
        for port in out_ports_all:
            try:
                self.check_wire(type_s=port.port_type,
                                type_r=port.destination.port_type,
                                allow_top=allow_top)
            except DeltaTypeError as port_type_err:
                raise DeltaTypeError(
                    port_type_err.args[0] + f'\n{port=}') from port_type_err

        return True

    def select_bodies(self,
                      exclusions: List[object] = None,
                      preferred: List[object] = None,
                      override=True):
        """Shortcut to selecting bodies accross whole graph.
        Applies exclusion rules then selects the first valid body for each
        node, preferred bodies selected if available.

        Returns
        -------
        bool
            ``True`` if all nodes now have a ``body``.
        """
        exclusions = exclusions if exclusions is not None else []
        preferred = preferred if preferred is not None else []
        all_selected = True
        for node in self.nodes:
            is_selected = node.select_body(exclusions, preferred, override)
            all_selected = all_selected and is_selected
        return all_selected

    @staticmethod
    def check_wire(type_s: BaseDeltaType,
                   type_r: BaseDeltaType,
                   allow_top: bool = True):
        """Check that ``type_s`` sent by :py:class:`OutPort` can by received
        as ``type_r`` by :py:class:`InPort`.

        In case when ``type_s`` is an instance of
        :py:class:`Union<deltalanguage.data_types.Union>`, it is
        enforces that each each type is received, i.e. strict typing.

        If ``allow_top`` is True then the receiver type can be Top(), which
        accepts any sending type. This is useful when debugging in the Python
        simulator.

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

        if type_s == Top():
            raise DeltaTypeError("Sender type cannot be Top().")

        if type_r == type_s:
            return True

        if type_r == Top() and allow_top:
            return True
        elif type_r == Top():
            raise DeltaTypeError(
                "Receiving type cannot be Top() when allow_top is False.")

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
        Union[AbstractNode, List[AbstractNode]]
            Node or list of nodes matching this name.
        """
        nodes = [node for node in self.nodes if name == node.name]

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
        port_nodes : bool
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
            graph.add_node(node.full_name, name=node.full_name, type="block")
            for out_port in node.out_ports:
                if port_nodes:
                    src = f"out_{str(out_port.name)}"
                    graph.add_node(src,
                                   name=out_port.index,
                                   type="out_port")
                    graph.add_edge(node.full_name, src)
                    dest = f"in_{str(out_port.dest_port_name)}"
                    graph.add_node(dest,
                                   name=out_port.dest_port_index,
                                   type="in_port")
                    graph.add_edge(dest, out_port.dest_node_name)
                    graph.add_edge(src, dest, type=str(out_port.port_type))
                else:
                    src = out_port.index
                    dest = out_port.dest_port_index
                    graph.add_edge(node.full_name,
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
        if any(key >= 1 for (_, _, key) in graph.edges):
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
    def from_capnp(cls,
                   capnp_obj: Union[capnp._DynamicStructReader,
                                    capnp._DynamicStructBuilder],
                   lvl: int = logging.ERROR):
        """Create and return a DeltaGraph based on deserialised .df file.

        Parameters
        ----------
        capnp_obj : Union[capnp._DynamicStructReader, capnp._DynamicStructBuilder]
            capnp data.
        lvl : int, optional
            lvl for logging on the created DeltaGraph object,
            by default logging.ERROR.


        Returns
        -------
        DeltaGraph
        """
        graph = cls(capnp_obj.name, lvl)

        # Initialise all nodes with their bodies and in ports
        for capnp_node in capnp_obj.nodes:

            # Create body objects
            bodies = []
            for body_id in capnp_node.bodies:
                capnp_body = capnp_obj.bodies[body_id]
                which_body = capnp_body.which()
                if "python" in which_body:
                    body = dill.loads(capnp_body.python.dillImpl)
                elif "interactive" in which_body:
                    body = dill.loads(capnp_body.interactive.dillImpl)
                else:
                    raise ValueError("Body has invalid type. Not all bodies are"
                                     " currently supported for deserialisation.")
                bodies.append(body)

            # Name ID stripping
            name = '_'.join(capnp_node.name.split('_')[:-1])

            # Create node object with bodies attached
            node = PythonNode(graph, bodies, inputs=None,
                              pos_in_nodes=[], kw_in_nodes={},
                              outputs=None, name=name)

            # Create and add InPorts and inputs
            inputs = []
            for capnp_in_port in capnp_node.inPorts:
                port_type = dill.loads(capnp_in_port.type)
                if capnp_in_port.optional:
                    port_type = Optional(port_type)
                inputs.append((capnp_in_port.name, port_type))
                node.add_in_port(capnp_in_port.name, port_type)

            node.inputs = OrderedDict(inputs)

        # Create mapping between OutPorts and the already existing InPorts
        port_dests = {}
        for wire in capnp_obj.graph:
            dest_node = capnp_obj.nodes[wire.destNode]
            dest_index = dest_node.inPorts[wire.destInPort].name

            # Find the dest port that has the correct index
            dest_port = None
            for port in graph.nodes[wire.destNode].in_ports:
                if dest_index == port.index:
                    dest_port = port
                    break

            src_port_indicies = (wire.srcNode, wire.srcOutPort)
            port_dests[src_port_indicies] = dest_port

        # Create and add OutPorts and outputs
        for i, capnp_node in enumerate(capnp_obj.nodes):
            outputs = []
            node = graph.nodes[i]
            for j, capnp_out_port in enumerate(capnp_node.outPorts):
                port_type = dill.loads(capnp_out_port.type)
                port_index = capnp_out_port.name
                dest_port = port_dests[(i, j)]
                outputs.append((port_index, port_type))
                node.out_ports.append(OutPort(port_index,
                                              port_type,
                                              dest_port,
                                              node))
            node.outputs = OrderedDict(outputs)

        return graph

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
