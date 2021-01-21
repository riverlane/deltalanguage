"""Module for defining the decorators for making python functions into
DeltaBlocks and DeltaMethods
"""

from __future__ import annotations
from functools import wraps
from inspect import _empty, signature
import logging
from typing import (TYPE_CHECKING,
                    Callable,
                    Dict,
                    Optional,
                    OrderedDict,
                    Tuple,
                    Type,
                    Union)

import attr

from deltalanguage.data_types import (BaseDeltaType,
                                      DOptional,
                                      DeltaTypeError,
                                      ForkedReturn,
                                      NoMessage,
                                      as_delta_type)
from ._delta_graph import DeltaGraph
from ._node_classes.interactive_node import (InteractiveFuncType,
                                             PyInteractiveNode)
from ._node_classes.real_nodes import PythonNode
from ._node_factories import py_method_node_factory, py_node_factory

if TYPE_CHECKING:
    from deltalanguage.wiring import Latency


def get_func_in_params_out_type(
    a_func: Callable,
    is_method: bool,
    node_key: Optional[str] = None
) -> Tuple[OrderedDict[str, Union[BaseDeltaType, DOptional]],
           Union[BaseDeltaType, ForkedReturn]]:
    """Helper function to extract input and output types of a node function.

    Parameters
    ----------
    a_func : Callable
        The function to analyse.
    is_method : bool
        Flag to specify if function is a class method.
    node_key : Optional[str]
        Keyword argument used for providing the node to the block, included for
        some logic purposes.

    Returns
    -------
    OrderedDict[str, Union[BaseDeltaType, DOptional]]
        Types of the in parameters.
    Union[BaseDeltaType, ForkedReturn]
        Type of the output the node to be made.

    Raises
    ------
    TypeError
        Raised if either the input or output types aren't specified in the
        function signature.
    """
    func_args = signature(a_func).parameters
    out_type = signature(a_func).return_annotation

    in_params = OrderedDict()
    for i, (arg_name, arg_param) in enumerate(func_args.items()):

        # first argument should always be 'self' for a method
        if i == 0 and is_method:
            continue

        if arg_param.annotation == _empty:
            raise TypeError(
                "Must specify the type of argument " +
                f"'{arg_name}' as annotation in " +
                f"function '{a_func.__name__}'"
            )

        if node_key and arg_param.annotation == PythonNode:
            continue

        delta_type_in = as_delta_type(arg_param.annotation)
        if not isinstance(delta_type_in, (BaseDeltaType, DOptional)):
            raise DeltaTypeError(f"Unsupported type={arg_param.annotation}")

        in_params[arg_name] = delta_type_in

    if out_type == _empty:
        raise TypeError(
            "Must specify the return type of " +
            f"function '{a_func.__name__}' as an annotation"
        )

    delta_type_out = as_delta_type(out_type)
    if delta_type_out is not NoMessage:
        if not isinstance(delta_type_out, (BaseDeltaType, ForkedReturn)):
            raise DeltaTypeError(f"Unsupported type={out_type}")

    return in_params, delta_type_out


def DeltaBlock(
    name: str = None,
    allow_const: bool = True,
    node_key: Optional[str] = None,
    in_port_size: int = 0,
    latency: Latency = None,
    lvl: int = logging.ERROR
):
    """Decorator to turn a function to a block for use in
    :py:class:`DeltaGraph`.

    If evaluated in the context of :py:class:`DeltaGraph` it will
    return a stateless node, which means that the output of such a node is
    fully determined by its inputs; exactly as it happens in functional
    programming.

    The node is evaluated when all compulsory inputs are provided.
    By default each input is compulsory, in order to make it optional use
    :py:class:`DOptional<deltalanguage.data_types.DOptional>` wrapper.

    .. warning::
        If a node does not have compulsory inputs then it will be evaluated
        continuesly and this can significantly slow down the entire runtime.

    Parameters
    ----------
    name : str
        The name of the node to be made.
    allow_const : bool
        If ``True`` and all inputs are constant then the output of this node is
        calculated only once, cached, and reused at each request.
        This used to reduce the computation load on the runtime stage.
    node_key : Optional[str]
        Keyword argument used for providing the node to the block, in case the
        user wants to debug sending & receiving messages in an interactive
        console. Note that this should only be used for debugging; for
        Deltaflow programs in production it should be sufficient to use the
        inputs and return values of a block for communications.
    in_port_size : int
        The maximum size of the node's in ports.
        If 0 then unlimited size.
    latency : Latency
        The estimated latency for running the body.
    lvl : int
        Logging level for the node.


    .. note::
        The function's inputs and outputs have to be typed, otherwise
        the decorator will raise an error.


    Examples
    --------
    The decorated function can be used as a normal python function:

    .. code-block:: python

        >>> from deltalanguage.lib import StateSaver
        >>> from deltalanguage.runtime import DeltaPySimulator
        >>> from deltalanguage.wiring import DeltaBlock, DeltaGraph

        >>> @DeltaBlock()
        ... def foo(a: int) -> int:
        ...     return a + 5

        >>> foo(5)
        10

    The exact same function can be used in the context of
    :py:class:`DeltaGraph`:

    .. code-block:: python

        >>> s = StateSaver(object, verbose=True)

        >>> with DeltaGraph() as graph:
        ...     foo_out = foo(5)
        ...     s.save_and_exit(foo_out) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        saving 10

    Nodes can also have multiple inputs:

    .. code-block:: python

        >>> @DeltaBlock()
        ... def bar(a: int, b: int) -> int:
        ...     return a*b

    Make sure that inputs of such nodes are not mixed up. For this one can
    use keyworded arguments, exactly as in python:

    .. code-block:: python

        >>> with DeltaGraph() as graph:
        ...     s.save_and_exit(bar(a=9, b=9)) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        saving 81

    For multiple outputs please refer to examples for
    :py:func:`make_forked_return<deltalanguage.data_types.make_forked_return>`.
    """
    def decorator(a_func):

        in_params, out_type = get_func_in_params_out_type(
            a_func, False, node_key
        )

        @wraps(a_func)
        def decorated(*args, **kwargs):
            """If there is currently an active :py:class:`DeltaGraph`,
            return a node constructed using the node factory.

            Parameters
            ----------
            args
                Either arguments to be used to evaluate the function or nodes
                to link to this node.
            kwargs
                Either keyworded arguments to be used to evaluate the function
                or nodes to link to this node.

            Returns
            -------
            the result of function evaluation or the created node
            """
            if DeltaGraph.stack():
                # there is currently an active DeltaGraph so use node factory
                current_graph = DeltaGraph.current_graph()
                return py_node_factory(current_graph,
                                       allow_const,
                                       a_func,
                                       in_params,
                                       out_type,
                                       *args,
                                       name=name or a_func.__name__,
                                       node_key=node_key,
                                       in_port_size=in_port_size,
                                       latency=latency,
                                       lvl=lvl,
                                       **kwargs)
            else:
                # No DeltaGraph active so evaluate function as usual
                return a_func(*args, **kwargs)

        decorated.original = in_params, out_type, a_func
        return decorated
    return decorator


def DeltaMethodBlock(
    name: str = None,
    node_key: Optional[str] = None,
    in_port_size: int = 0,
    latency: Latency = None,
    lvl: int = logging.ERROR
):
    """Decorator to turn a class method to a block for use in
    :py:class:`DeltaGraph`.

    If evaluated in the context of :py:class:`DeltaGraph` it will
    return a node that can have an internal state stored in the instance of
    the target class. THus the output determined by not only the inputs but
    also by the internal state that can change.

    .. warning::
        The internal state is a very powerful concept that makes the Deltaflow
        language significantly more expressive, but also can lead to
        non-deterministic results. Please refer to the tutorial
        (TODO add the link) that cover covers this.

    The node is evaluated when all compulsory inputs are provided.
    By default each input is compulsory, in order to make it optional use
    :py:class:`DOptional<deltalanguage.data_types.DOptional>` wrapper.

    .. warning::
        If a node does not have compulsory inputs then it will be evaluated
        continuesly and this can significantly slow down the entire runtime.

    Parameters
    ----------
    name : str
        The name of the node to be made.
    node_key : Optional[str]
        Keyword argument used for providing the node to the block, in case the
        user wants to debug sending & receiving messages in an interactive
        console. Note that this should only be used for debugging; for
        Deltaflow programs in production it should be sufficient to use the
        inputs and return values of a block for communications.
    in_port_size : int
        The maximum size of the node's in ports.
        If 0 then unlimited size.
    latency : Latency
        The estimated latency for running the body.
    lvl : int
        Logging level for the node.


    .. note::
        The method's inputs and outputs have to be typed, otherwise
        the decorator will raise an error.


    Examples
    --------
    The decorated method can be used as a normal python class method:

    .. code-block:: python

        >>> from deltalanguage.lib import StateSaver
        >>> from deltalanguage.runtime import DeltaPySimulator
        >>> from deltalanguage.wiring import DeltaBlock, DeltaGraph

        >>> class MyClass:
        ...
        ...     def __init__(self, x):
        ...         self.x = x
        ...
        ...     @DeltaMethodBlock()
        ...     def bar(self, a: int) -> int:
        ...         return self.x + a

        >>> my_obj = MyClass(10)
        >>> print(my_obj.bar(5))
        15

    The exact same object can be used in the context of
    :py:class:`DeltaGraph`:

    .. code-block:: python

        >>> s = StateSaver(object, verbose=True)

        >>> with DeltaGraph() as graph:
        ...     s.save_and_exit(my_obj.bar(5)) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        saving 15

    However if the internal state of the object changes (before or during)
    a runtime handles the same graph, the result will change:

    .. code-block:: python

        >>> my_obj.x = 15

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        saving 20

    Nodes can also have multiple inputs exactly as
    :py:class:`DeltaBlock`.

    In case of multiple outputs please refer to examples for
    :py:func:`make_forked_return<deltalanguage.data_types.make_forked_return>`.
    """
    def decorator(a_func):

        in_params, out_type = get_func_in_params_out_type(
            a_func, True, node_key
        )

        @wraps(a_func)
        def decorated(obj, *args, **kwargs):
            """If there is currently an active DeltaGraph, return a node
            constructed using the node factory.

            Parameters
            ----------
            obj
                Instantiated object of the class a_func is from.
            args
                Either arguments to be used to evaluate the function or nodes
                to link to this node.
            kwargs
                Either kwarguments to be used to evaluate the function or nodes
                to link to this node.

            Returns
            -------
            The result of function evaluation or the created node.
            """
            if DeltaGraph.stack():
                # there is currently an active DeltaGraph so use node factory
                current_graph = DeltaGraph.current_graph()
                return py_method_node_factory(current_graph,
                                              a_func,
                                              obj,
                                              in_params,
                                              out_type,
                                              *args,
                                              name=name or a_func.__name__,
                                              node_key=node_key,
                                              in_port_size=in_port_size,
                                              latency=latency,
                                              lvl=lvl,
                                              **kwargs)
            else:
                # No DeltaGraph active so evaluate function as usual
                return a_func(obj, *args, **kwargs)

        decorated.original = a_func
        return decorated
    return decorator


@attr.s
class InteractiveProcess:
    """The type of block running inside an interactive node, manually
    annotated with input and output type.

    Attributes
    ----------
    proc : InteractiveFuncType
        Class instance this node operates on.
    arg_types : Dict[str, Type]
        The types of the in parameters to the node to be made.
    return_type : Type
        The type of the output for the node to be made.
    name : str
        The name of the node to be made.
    in_port_size : int
        The maximum size of the node's in ports. If 0 then unlimited size.
    lvl : int
        Logging level for the node. By default logging.ERROR.
    """
    proc: InteractiveFuncType = attr.ib()
    arg_types: Dict[str, Type] = attr.ib()
    return_type: Type = attr.ib()
    name: str = attr.ib()
    in_port_size: int = attr.ib(default=0)
    lvl: int = attr.ib(default=logging.ERROR)

    def call(self, *params, **kwargs):
        """Turn this InteractiveProcess into a node, and wire it up to the
        nodes given in kwargs as inputs.
        """
        if params:
            raise ValueError(
                "Please only use keyword arguments for interactive nodes."
            )
        graph = DeltaGraph.current_graph()
        new_node = PyInteractiveNode(graph, self, **kwargs)
        return new_node


def Interactive(in_params: Dict[str, Type],
                out_type: Type,
                name=None,
                in_port_size: int = 0,
                lvl: int = logging.ERROR) -> Callable[..., InteractiveProcess]:
    """Decorator to turn a function of a special type (see examples)
    to a block for use in :py:class:`DeltaGraph`.

    The function used with this decorator is not meant to be on its own in
    contrast with :py:class:`DeltaBlock` and :py:class:`DeltaMethodBlock`.

    The types of inputs and outputs have to be defined using ``in_params`` and
    ``out_type``. By default each input is compulsory, in order to make it
    optional use :py:class:`DOptional<deltalanguage.data_types.DOptional>`
    wrapper.

    Unlike nodes created via :py:class:`DeltaBlock` and
    :py:class:`DeltaMethodBlock`, the interactive node is evaluated only once.
    Thus it's in the user's responsibility to specify when and which
    inputs and outputs are used. This is done via ``send`` and ``receive``
    methods.

    The inputs and outputs can be received and sent simultaneously
    or just partially, which gives a lot of flexibility in comparison with
    :py:class:`DeltaBlock` and :py:class:`DeltaMethodBlock`.
    For instance, if a compulsory input is expected then by calling ``receive``
    on this input the node execution will be frozen until the input is provided.
    On the other hand, calling ``receive`` for an optional input will not
    freeze the node and simply use ``None`` if no input is provided at
    this instance of time.

    Parameters
    ----------
    in_params : Dict[str, Type]
        The types of the in parameters to the node to be made.
    out_type : Type
        The type of the output for the node to be made.
    name : str
        The name of the node to be made.
    in_port_size : int
        The maximum size of the node's in ports.
        If 0 then unlimited size.
    lvl : int
        Logging level for the node.

    Examples
    --------
    Let's look at the syntax first.
    Here is an example where all inputs are received simultaneously several
    times, before the output is sent off, then the node becomes idle:

    .. code-block:: python

        >>> from deltalanguage.lib.primitives import StateSaver
        >>> from deltalanguage.runtime import DeltaPySimulator
        >>> from deltalanguage.wiring import Interactive, PyInteractiveNode

        >>> @Interactive(in_params={"a": int, "b": int}, out_type=int)
        ... def foo(node: PyInteractiveNode):
        ...     internal_memory = 0
        ...
        ...     for i in range(10):
        ...         inputs = node.receive()
        ...         internal_memory += inputs["a"] * inputs["b"]
        ...
        ...     node.send(internal_memory)

    .. note::
        :py:class:`PyInteractiveNode` is simply used to syntax highlight.

    To use this node in the context of :py:class:`DeltaGraph` a special
    method ``node`` should be used:

    .. code-block:: python

        >>> s = StateSaver(int, verbose=True)

        >>> with DeltaGraph() as graph:
        ...     s.save_and_exit(foo.call(a=4, b=5)) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        saving 200

    Here is the case when inputs are read independently:

    .. code-block:: python

        >>> @Interactive(in_params={"a": int, "b": int}, out_type=int)
        ... def bar(node: PyInteractiveNode):
        ...     internal_memory = 0
        ...
        ...     for i in range(10):
        ...         if i%2 == 0:
        ...             internal_memory += node.receive("a")
        ...         else:
        ...             internal_memory -= node.receive("b")
        ...
        ...     node.send(internal_memory)

        >>> with DeltaGraph() as graph:
        ...     s.save_and_exit(bar.call(a=4, b=5)) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        saving -5

    In case of multiple outputs make sure to call
    :py:func:`make_forked_return<deltalanguage.data_types.make_forked_return>`
    beforehand, then the outputs can be send out in any configuration:

    .. code-block:: python

        >>> from deltalanguage.data_types import make_forked_return

        >>> TwoIntsT, TwoIntsC = make_forked_return({'x': int, 'y': int})

        >>> @Interactive(in_params={"a": int}, out_type=TwoIntsT)
        ... def baz(node: PyInteractiveNode):
        ...     for i in range(10):
        ...         a = node.receive("a")
        ...         if a%3 == 0:
        ...             node.send(TwoIntsC(x=a, y=None))
        ...         elif a%3 == 1:
        ...             node.send(TwoIntsC(x=None, y=a))
        ...         else:
        ...             node.send(TwoIntsC(x=a, y=a))
    """
    def decorator(a_func: InteractiveFuncType):
        proc = InteractiveProcess(a_func,
                                  in_params,
                                  out_type,
                                  name or a_func.__name__,
                                  in_port_size,
                                  lvl)
        return proc
    return decorator
