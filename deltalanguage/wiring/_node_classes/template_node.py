import logging
from typing import (Callable,
                    Dict,
                    Type,
                    Union)

from deltalanguage.data_types import BaseDeltaType, as_delta_type

from .._decorators import get_func_in_params_out_type
from .._delta_graph import DeltaGraph
from .._node_factories import ForkedNode, get_py_const_node_arg_num
from .node_bodies import PyConstBody, PyFuncBody
from .real_nodes import AbstractNode, PythonNode


class TemplateNode(PythonNode):
    """Node class to represent nodes that have yet to have their bodies
    specified, but that have a pre-defined interface.

    The main pourpose of this type of node is that its body can be defined
    at a later stage of the Deltaflow programming, also known as running stage,
    as opposed to the programming stage where the graph is defined.

    Use :py:class:`template_node_factory` for construction in the
    context of :py:class:`DeltaGraph`.

    Parameters
    ----------
    graph : DeltaGraph
        Graph this node is a member of.
    kw_in_nodes : Dict[str, AbstractNode]
        The input nodes to this template node, specified by kwargs
    return_type : Union[Type, BaseDeltaType]
        The required return type of this template node
    name : str
        Node name.
    arg_types : Dict[str, Union[Type, BaseDeltaType]]
        The types of each in port. Required if input nodes do not have a
        specified type, such as with placeholder nodes.
    in_port_size : int
        The maximum size of the node's in ports. If 0 then unlimited size.
    lvl : int
        Logging level for the node.
    """

    def __init__(
        self,
        graph: DeltaGraph,
        kw_in_nodes: Dict[str, AbstractNode],
        return_type: Union[Type, BaseDeltaType],
        name: str = None,
        arg_types: Dict[str, Union[Type, BaseDeltaType]] = {},
        in_port_size: int = 0,
        lvl: int = logging.ERROR
    ):
        name_prefix = "template"

        if name is not None:
            name_prefix = name_prefix + "_" + name

        super().__init__(
            graph,
            None,
            return_type=as_delta_type(return_type),
            name=name_prefix,
            lvl=lvl
        )

        self._in_params = {}
        for k, v in kw_in_nodes.items():
            # First check if input type specified in arg_types
            if k in arg_types:
                arg_type = as_delta_type(arg_types[k])
            else:
                arg_type = None
            # Now check if input type is specified in nodes
            if isinstance(v, ForkedNode):
                # In input type is forked, then get specified port type
                ret_type = v.return_type.elem_dict[v.index]
            else:
                ret_type = v.return_type
            if not isinstance(ret_type, BaseDeltaType):
                # If we get here then type is not specified
                ret_type = None
            if (arg_type is not None) and (ret_type is not None):
                # We have type define in arg_types and input
                # check if they match
                if arg_type == ret_type:
                    self._in_params[k] = arg_type
                else:
                    raise TypeError(f"Argument {k} specified as {arg_type}"
                                    f" but is actually {ret_type}")
            elif arg_type is not None:
                self._in_params[k] = arg_type
            elif ret_type is not None:
                self._in_params[k] = ret_type
            else:
                # Type cannot be found
                raise TypeError(f"No type specified for argument {k}")
        self._kw_in_nodes = kw_in_nodes
        self._in_port_size = in_port_size

        #Const property currently unknown
        self._is_const = None

        self._create_upstream_ports(
            self._in_params,
            self._kw_in_nodes,
            in_port_size=self._in_port_size
        )

    def specify_by_func(
        self,
        my_func: Callable,
        allow_const: bool = True,
    ):
        """Function to pass a function as a body to the node in a post-hoc
        fashion.

        Parameters
        ----------
        my_func : Callable
            Function that will define the node body.
        allow_const : bool, optional
            Flag to specify if the node body can be constant, by default True

        Raises
        ------
        TypeError
            If the return type of the passed function does not match that
            required by the template node interface.
        TypeError
            If the input types of the passed function do not match those
            required by the template node interface.
        """

        in_params, out_type = get_func_in_params_out_type(
            my_func, False
        )

        if isinstance(self.return_type, BaseDeltaType):
            out_type = as_delta_type(out_type)

        if out_type != self.return_type:
            raise TypeError(
                f"Python body in {self.name} requries return " +
                f"type of {self.return_type}!"
            )

        for arg, arg_type in in_params.items():

            if isinstance(self._in_params[arg], BaseDeltaType):
                arg_type = as_delta_type(arg_type)

            if self._in_params[arg] != arg_type:
                raise TypeError(
                    f"Python body in {self.name} requries type " +
                    f"{self._in_params[arg]} for argument {arg}!"
                )

        num_const = get_py_const_node_arg_num([], self._kw_in_nodes)

        if allow_const and num_const == len(self._kw_in_nodes):
            self._body = PyConstBody(my_func, **self._kw_in_nodes)
            self._is_const = True
        else:
            self._body = PyFuncBody(my_func)
            self._is_const = False

    def is_const(self):
        """Method to return state of self._const.

        Returns
        -------
        bool
            If the current body is constant or not.
        """
        return self._is_const
