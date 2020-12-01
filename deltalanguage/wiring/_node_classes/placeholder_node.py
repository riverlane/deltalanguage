"""Class to represent a placeholder node that can be replaced with a real node.
"""

from __future__ import annotations
import logging
from typing import (TYPE_CHECKING,
                    Callable,
                    Dict,
                    Iterable,
                    List,
                    Optional,
                    Tuple)

from deltalanguage.logging import make_logger
from .._decorators import get_func_in_params_out_type
from .._node_factories import py_method_node_factory, py_node_factory

from .abstract_node import ForkedNode, ProxyNode
from .interactive_node import PyInteractiveNode

if TYPE_CHECKING:
    from .._decorators import InteractiveProcess
    from .._delta_graph import DeltaGraph
    from .abstract_node import AbstractNode
    from .port_classes import InPort


log = make_logger(logging.WARNING, "PROXY NODES")


class PlaceholderNode(ProxyNode):
    """Node class to represent nodes that have yet to be specified.

    These nodes have to be specified in the context of :py:class:`DeltaGraph`,
    their main use case is creation of cyclic dependencies in the graph,
    i.e. loops.

    Use :py:class:`placeholder_node_factory` for construction in the
    context of :py:class:`DeltaGraph`.

    Parameters
    ----------
    graph : DeltaGraph
        Graph this node is a part of.
    name : str
        Name is used to access this placeholder when we want to replace
        it with a real node.
    args
        Nodes specified positionally that will be output to the node
        this placeholder is replaced by.
    kwargs
        Nodes specified via kw that will be output to the node
        this placeholder is replaced by.
    """

    def __init__(self,
                 graph: DeltaGraph,
                 name: str,
                 *args: Iterable[AbstractNode],
                 **kwargs):
        # No referee to give to super until node is specified
        super().__init__()
        self.graph = graph
        self.key = name
        # Register myself as a proxy under a given name
        self.graph.add_placeholder(self.key, self)

        # Store of nodes to be used to make in-ports at a later time.
        # Ignored if this placeholder is specified by
        # `specify_by_node` or `specify_by_process`.
        self.future_in_port_args: Iterable[AbstractNode] = args

        # Store of nodes to be used to make in-ports at a later time.
        # Ignored if this placeholder is specified by "specify_by_node".
        self.future_in_port_kwargs: Dict[str, AbstractNode] = kwargs

        # Store of port_name, port_destination, index pairs used to
        # create out-ports later on.
        # There are currently no out-ports as only in-ports are specified
        # at init time.
        self.future_out_ports: List[Tuple[InPort, Optional[str]]] = []

    def __getattr__(self, item):
        """Get forked node to represent that indexed access or the result of
        the normal attribute request.
        """
        fetched = getattr(self.referee, item, None)

        if fetched is None:
            return ForkedNode(self, item)

        return fetched

    def add_out_port(self, port_destination: InPort, index=None):
        """If this placeholder has been specified, we will add the out-port
        to the referee.

        If this placeholder is yet to be specified, we will store this data
        for later use.
        """
        if self.referee is None:
            self.future_out_ports.append((port_destination, index))
        else:
            self.referee.add_out_port(port_destination, index)

    def specify_by_func(self,
                        my_func: Callable,
                        allow_const: bool = True,
                        node_key: Optional[str] = None,
                        lvl: int = logging.ERROR):
        """Makes this placeholder no longer a placeholder, it acts like
        the node constructed using the given function.

        In-ports and out-ports on the placeholder get added to the new node.

        Parameters
        ----------
        my_func : Callable
            Function we will make into a node that this placeholder will
            represent.
        allow_const : bool
            Flag to specify if the node body can be constant, by default True.
        node_key : Optional[str]
            Keyword argument used for providing the node to the block, in case the
            user wants to debug sending & receiving messages in an interactive
            console. Note that this should only be used for debugging; for
            Deltaflow programs in production it should be sufficient to use the
            inputs and return values of a block for communications.
        lvl : int
            Logging level for the node. By default logging.ERROR.
        """

        in_params, out_type = get_func_in_params_out_type(
            my_func, False, node_key
        )

        # Construct a real node then set it as my referee
        my_referee = py_node_factory(self.graph,
                                     allow_const,
                                     my_func,
                                     in_params,
                                     out_type,
                                     *self.future_in_port_args,
                                     name=self.key,
                                     node_key=node_key,
                                     lvl=lvl,
                                     **self.future_in_port_kwargs)
        self.referee = my_referee

        # Add the out ports needed for the specified node
        for destination, index in self.future_out_ports:
            self.add_out_port(destination, index)

        # remove myself from the list of active placeholders for my graph
        self.graph.placeholders.pop(self.key)

    def specify_by_process(self, process: InteractiveProcess, **extra_kwargs):
        """Make this placeholder into a PyInteractiveNode with the given
        process function, and the given type of inputs and outputs.

        Parameters
        ----------
        process : InteractiveProcess
            Function of type (PyInteractiveNode -> None) packed with its
            input and output types.
        extra_kwargs
            Additional inputs to pass to the Interactive Node constructor.
        """
        if self.future_in_port_args:
            log.warning("Positional arguments dropped when specifying "
                        "placeholder as PyInteractiveNode")

        my_referee = PyInteractiveNode(self.graph,
                                       process,
                                       **self.future_in_port_kwargs,
                                       **extra_kwargs)
        self.referee = my_referee

        # Add destination out-ports
        for destination, index in self.future_out_ports:
            self.add_out_port(destination, index)

        # remove myself from the list of active placeholders for my graph
        self.graph.placeholders.pop(self.key)

    def specify_by_method(self,
                          method_func: Callable,
                          instance: object,
                          node_key: Optional[str] = None,
                          lvl: int = logging.ERROR):
        """Makes this placeholder no longer a placeholder, it acts like the
        node constructed using the given function.

        In-ports and out-ports on the placeholder get added to the new node.

        Parameters
        ----------
        instance : object
            Instantiated object this nodes method func will run on.
        method_func : Callable
            Method function to run.
        node_key : Optional[str]
            Keyword argument used for providing the node to the block, in case the
            user wants to debug sending & receiving messages in an interactive
            console. Note that this should only be used for debugging; for
            Deltaflow programs in production it should be sufficient to use the
            inputs and return values of a block for communications.
        """

        in_params, out_type = get_func_in_params_out_type(
            method_func, True, node_key
        )

        # Construct a real node then set it as my referee
        my_referee = py_method_node_factory(self.graph,
                                            method_func,
                                            instance,
                                            in_params,
                                            out_type,
                                            *self.future_in_port_args,
                                            name=self.key,
                                            node_key=node_key,
                                            lvl=lvl,
                                            **self.future_in_port_kwargs)
        self.referee = my_referee

        # Add the out ports needed for the specified node
        for destination, index in self.future_out_ports:
            self.add_out_port(destination, index)

        # remove myself from the list of active placeholders for my graph
        self.graph.placeholders.pop(self.key)

    def specify_by_node(self, node: AbstractNode):
        """Makes this placeholder no longer a placeholder, it acts like
        the given node where this placeholder has been used as input, i.e
        where this placeholder has an out-port: add this out-port to
        the given node.

        Parameters
        ----------
        node : AbstractNode
            Node this placeholder now represents.
        """
        self.referee = node

        if self.future_in_port_args or self.future_in_port_kwargs:
            # specify_by_func should be used instead if this occurs
            log.warning("Placeholder at %s is being specified by "
                        "node but it already has input nodes itself.", self.key)

        # Add the out ports needed for the specified node
        for destination, index in self.future_out_ports:
            self.add_out_port(destination, index)

        # remove myself from the list of active placeholders for my graph
        self.graph.placeholders.pop(self.key)
