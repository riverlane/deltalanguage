"""Factories to aid in the construction of nodes."""

from __future__ import annotations
import inspect
import logging
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Type, Union

from deltalanguage.data_types import BaseDeltaType, DOptional, DeltaTypeError
from deltalanguage.logging import make_logger

from ._node_classes.abstract_node import AbstractNode, ForkedNode
from ._node_classes.real_nodes import (PyConstNode,
                                       PyFuncNode,
                                       PyMethodNode,
                                       PyMigenNode,
                                       as_node)

if TYPE_CHECKING:
    from deltalanguage.wiring import Latency


log = make_logger(logging.WARNING, "Node Factory")


def py_node_factory(graph,
                    allow_const: bool,
                    node_func: Callable,
                    in_params: Dict[str, Union[BaseDeltaType, DOptional]],
                    out_type: Type,
                    *args,
                    name: str = None,
                    latency: Latency = None,
                    node_key: Optional[str] = None,
                    in_port_size: int = 0,
                    lvl: int = logging.ERROR,
                    **kwargs):
    """Node factory for creating normal python-based nodes.

    Parameters
    ----------
    in_params : Dict[str, Union[BaseDeltaType, DOptional]]
        The types of the in parameters to the node to be made.
    out_type : Type
        The type of the out-put for the node to be made.
    name : str
        The name of the node to be made.
    latency : Latency
        The estimated latency for running the body.
    graph : DeltaGraph
        Graph the node will belong to.
    node_func : Callable
        Function that the node will contain as its body.
    in_port_size : int
        The maximum size of the node's in ports. If 0 then unlimited size.
    allow_const : bool
        Whether this function can return a constant node.
    node_key : Optional[str]
        Keyword argument used for providing the node to the block, in case the
        user wants to debug sending & receiving messages in an interactive
        console. Note that this should only be used for debugging; for
        Deltaflow programs in production it should be sufficient to use the
        inputs and return values of a block for communications.
    args
        Nodes to create in-ports for
    kwargs
        Nodes to create in-ports for by kw

    Returns
    -------
    RealNode
        Created node, can be PyConstNode or PyFuncNode
    """
    are_optional_inputs = False
    for in_type in in_params.values():
        if isinstance(in_type, DOptional):
            are_optional_inputs = True
        elif not isinstance(in_type, BaseDeltaType):
            raise DeltaTypeError('Unsupported data type')

    # Turn all input nodes into constant py nodes if they are node already
    # some kind of node
    pos_in_nodes = [as_node(arg, graph) for arg in args]
    kw_in_nodes = {name: as_node(arg, graph) for (name, arg) in kwargs.items()}

    # Count how many input nodes are constant
    num_const = get_py_const_node_arg_num(pos_in_nodes, kw_in_nodes)

    # condition for a constant node
    if (allow_const
        and num_const == len(pos_in_nodes) + len(kw_in_nodes)
        and node_key is None
            and not are_optional_inputs):
        constructed_node = PyConstNode(graph,
                                       node_func,
                                       in_params,
                                       out_type,
                                       pos_in_nodes,
                                       kw_in_nodes,
                                       name=name,
                                       latency=latency,
                                       lvl=lvl)
    else:
        constructed_node = PyFuncNode(graph,
                                      node_func,
                                      in_params,
                                      out_type,
                                      pos_in_nodes,
                                      kw_in_nodes,
                                      name=name,
                                      latency=latency,
                                      node_key=node_key,
                                      in_port_size=in_port_size,
                                      lvl=lvl)

    log.debug("making %s: %s", type(constructed_node), constructed_node.name)

    return constructed_node


def py_method_node_factory(graph,
                           node_func: Callable,
                           obj,
                           in_params: Dict[str, Type],
                           out_type: Type,
                           *args,
                           is_migen: bool = False,
                           name: str = None,
                           latency: Latency = None,
                           node_key: Optional[str] = None,
                           in_port_size: int = 0,
                           lvl: int = logging.ERROR,
                           **kwargs):
    """Node factory for creating nodes that are methods that operate on some
    class instance.

    Parameters
    ----------
    in_params: Dict[str, Type]
        The types of the in parameters to the node to be made.
    out_type : Type
        The type of the out-put for the node to be made.
    name : str
        The name of the node to be made.
    latency : Latency
        The estimated latency for running the body.
    graph : DeltaGraph
        Graph these nodes will be a part of.
    node_func : Callable
        Function for the node body.
    in_port_size : int
        The maximum size of the node's in ports. If 0 then unlimited size.
    obj
        Class instance this node operates on.
    node_key : Optional[str]
        Keyword argument used for providing the node to the block, in case the
        user wants to debug sending & receiving messages in an interactive
        console. Note that this should only be used for debugging; for
        Deltaflow programs in production it should be sufficient to use the
        inputs and return values of a block for communications.
    args
        Node inputs to make in-ports for
    kwargs
        kw nodes to make in-ports for

    Returns
    -------
    RealNode
        Created node, of type PyMethodNode or PyMigenNode.
    """
    log.debug("Making method node with %s", node_func)
    assert list(inspect.signature(node_func).parameters.keys())[0] == "self"

    # Turn all input nodes into constant py nodes if they are node already
    # some kind of node
    pos_in_nodes = [as_node(arg, graph) for arg in args]
    kw_in_nodes = {name: as_node(arg, graph) for (name, arg) in kwargs.items()}

    if is_migen:
        constructed_node = PyMigenNode(graph,
                                       node_func,
                                       obj,
                                       in_params,
                                       out_type,
                                       pos_in_nodes,
                                       kw_in_nodes,
                                       name=name,
                                       latency=latency,
                                       node_key=node_key,
                                       in_port_size=in_port_size,
                                       lvl=lvl)
    else:
        constructed_node = PyMethodNode(graph,
                                        node_func,
                                        obj,
                                        in_params,
                                        out_type,
                                        pos_in_nodes,
                                        kw_in_nodes,
                                        name=name,
                                        latency=latency,
                                        node_key=node_key,
                                        in_port_size=in_port_size,
                                        lvl=lvl)

    log.debug("making %s: %s", type(constructed_node), constructed_node.name)

    return constructed_node


def get_py_const_node_arg_num(pos_nodes: List[AbstractNode],
                               kw_nodes: Dict[str, AbstractNode]):
    """Get the number of constant arguments in the arg list of a node.

    Parameters
    ----------
    pos_nodes : List[AbstractNode]
        Positionally specified nodes.
    kw_nodes : Dict[str, AbstractNode]
        Keyworded specified nodes.

    Returns
    -------
    int
        the number of nodes that are PyConst nodes
    """
    all_args = pos_nodes + list(kw_nodes.values())

    num_args = sum([isinstance(node, PyConstNode) for node in all_args])
    # for forked nodes, check if the referee is const
    for node in all_args:
        if isinstance(node, ForkedNode):
            if isinstance(node.referee, PyConstNode):
                num_args += 1

    return num_args
