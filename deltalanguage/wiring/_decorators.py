"""User facing decorators for building DeltaGraph nodes."""

from __future__ import annotations
from functools import wraps
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
                                      DeltaIOError,
                                      DeltaTypeError,
                                      DOptional,
                                      ForkedReturn,
                                      Void,
                                      as_delta_type)
from ._delta_graph import DeltaGraph
from ._node_classes.real_nodes import (as_node,
                                       get_func_in_params_out_type,
                                       PythonNode)
from ._node_classes.node_bodies import PyInteractiveBody
from ._node_factories import py_method_node_factory, py_node_factory

if TYPE_CHECKING:
    from deltalanguage.wiring import Latency


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

    If called in the context of :py:class:`DeltaGraph` it will
    return a stateless node, which means that the output of such a node is
    fully determined by its inputs; exactly as it happens in functional
    programming.

    The node is evaluated when all compulsory inputs are provided.
    By default each input is compulsory, in order to make it optional use
    :py:class:`DOptional<deltalanguage.data_types.DOptional>` wrapper.

    .. warning::
        If a node does not have compulsory inputs then it will be evaluated
        continuesly and this can significantly slow down a runtime simulator.
        If node does not have optional inputs consider using
        ``allow_const=True`` to improve performance.

    Parameters
    ----------
    name : str
        The name of the node to be made.
    allow_const : bool
        If ``True`` and all inputs are constant then the output of this node is
        calculated only once, cached, and reused at each request.
        This used to reduce the computation load.
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

        >>> import deltalanguage as dl

        >>> @dl.DeltaBlock()
        ... def foo(a: int) -> int:
        ...     return a + 5

        >>> foo(5)
        10

    The exact same function can be used in the context of
    :py:class:`DeltaGraph`:

    .. code-block:: python

        >>> s = dl.lib.StateSaver(object, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     foo_out = foo(5)
        ...     s.save_and_exit(foo_out) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 10

    Nodes can also have multiple inputs:

    .. code-block:: python

        >>> @dl.DeltaBlock()
        ... def bar(a: int, b: int) -> int:
        ...     return a*b

    Make sure that inputs of such nodes are not mixed up. For this one can
    use keyworded arguments, exactly as in python:

    .. code-block:: python

        >>> with dl.DeltaGraph() as graph:
        ...     s.save_and_exit(bar(a=9, b=9)) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
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

    If called in the context of :py:class:`DeltaGraph` it will
    return a node that can have an internal state stored in the instance of
    the target class. Thus the output determined by not only the inputs but
    also by the internal state that can change.

    .. warning::
        The internal state is a very powerful concept that makes the Deltaflow
        language significantly more expressive, but also can lead to
        non-deterministic results. Please refer to
        `Non-deterministic state history <tutorials/state_history.html>`_
        that cover this in detail.

    The node is evaluated when all compulsory inputs are provided.
    By default each input is compulsory, in order to make it optional use
    :py:class:`DOptional<deltalanguage.data_types.DOptional>` wrapper.

    .. warning::
        If a node does not have compulsory inputs then it will be evaluated
        continuesly and this can significantly slow down a runtime simulator.

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

        >>> import deltalanguage as dl

        >>> class MyClass:
        ...
        ...     def __init__(self, x):
        ...         self.x = x
        ...
        ...     @dl.DeltaMethodBlock()
        ...     def bar(self, a: int) -> int:
        ...         return self.x + a

        >>> my_obj = MyClass(10)
        >>> print(my_obj.bar(5))
        15

    The exact same object can be used in the context of
    :py:class:`DeltaGraph`:

    .. code-block:: python

        >>> s = dl.lib.StateSaver(object, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     s.save_and_exit(my_obj.bar(5)) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 15

    However if the internal state of the object changes (before or during),
    the result will change:

    .. code-block:: python

        >>> my_obj.x = 15

        >>> rt = dl.DeltaPySimulator(graph)
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
    proc : Callable[[PythonNode], None]
        Class instance this node operates on.
    arg_types : Dict[str, Type]
        The types of the in parameters to the node to be made.
    out_type : Type
        The type of the output for the node to be made.
    name : str
        The name of the node to be made.
    in_port_size : int
        The maximum size of the node's in ports. If 0 then unlimited size.
    lvl : int
        Logging level for the node.
        By default only error logs are displayed.
    """
    proc: Callable[[PythonNode], None] = attr.ib()
    arg_types: Dict[str, Type] = attr.ib()
    out_type: Type = attr.ib()
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
        my_body = PyInteractiveBody(self.proc)

        kw_in_nodes = {name: as_node(arg, graph)
                       for (name, arg) in kwargs.items()}

        new_node = PythonNode(graph,
                              [my_body],
                              self.arg_types,
                              [],
                              kw_in_nodes,
                              out_type=self.out_type,
                              name=self.name,
                              lvl=self.lvl,
                              in_port_size=self.in_port_size)
        return new_node


def Interactive(in_params: Dict[str, Type],
                out_type: Type,
                name: str = None,
                in_port_size: int = 0,
                lvl: int = logging.ERROR) -> Callable[..., InteractiveProcess]:
    """Decorator to turn a function of a special type (see examples)
    to an interactive node for use in :py:class:`DeltaGraph`.

    The function used with this decorator is not meant to be used on its own
    (i.e. outside of the graph) in contrast with
    :py:class:`DeltaBlock` and :py:class:`DeltaMethodBlock`.

    The types of inputs and outputs have to be defined using ``in_params`` and
    ``out_type``. By default each input is compulsory, in order to make it
    optional use :py:class:`DOptional<deltalanguage.data_types.DOptional>`
    wrapper.

    Unlike nodes created via :py:class:`DeltaBlock` and
    :py:class:`DeltaMethodBlock`, the interactive node is evaluated only once.
    Thus it's in the user's responsibility to specify when and which
    inputs and outputs are used.
    This is done via ``send`` and ``receive`` methods and shown in examples
    below.

    An interactive node's inputs/outputs can be received/sent simultaneously
    or partially, which gives a lot of flexibility in comparison with
    :py:class:`DeltaBlock` and :py:class:`DeltaMethodBlock`.
    For instance, if a compulsory input is expected then by calling ``receive``
    on this input the node execution will be frozen until the input is
    provided.
    On the other hand, calling ``receive`` for an optional input will not
    freeze the node and simply use ``None`` if no input is provided at
    this instance of time.

    An interactive node should use at least one input or output to communicate
    with other nodes, otherwise runtime simulators, e.g.
    :py:class:`DeltaPySimulator<deltalanguage.runtime.DeltaPySimulator>`,
    might be significantly slowed down by their schedulers.

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
    times, before the output is sent off once, then the node becomes idle:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> @dl.Interactive(in_params={"a": int, "b": int}, out_type=int)
        ... def foo(node: PythonNode):
        ...     internal_memory = 0
        ...
        ...     for i in range(10):
        ...         inputs = node.receive()
        ...         internal_memory += inputs["a"] * inputs["b"]
        ...
        ...     node.send(internal_memory)

    .. note::
        :py:class:`PythonNode` is used to help with syntax highlight.
        For instance when using a linting tool you can access definitions of
        `send` and `receive` methods and see their parameters.

    To use this node in the context of :py:class:`DeltaGraph` a special
    method ``node`` should be used:

    .. code-block:: python

        >>> s = dl.lib.StateSaver(int, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     s.save_and_exit(foo.call(a=4, b=5)) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 200

    Here is the case when inputs are read independently:

    .. code-block:: python

        >>> @dl.Interactive(in_params={"a": int, "b": int}, out_type=int)
        ... def bar(node: PythonNode):
        ...     internal_memory = 0
        ...
        ...     for i in range(10):
        ...         if i%2 == 0:
        ...             internal_memory += node.receive("a")
        ...         else:
        ...             internal_memory -= node.receive("b")
        ...
        ...     node.send(internal_memory)

        >>> with dl.DeltaGraph() as graph:
        ...     s.save_and_exit(bar.call(a=4, b=5)) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving -5

    In case of multiple outputs make sure to call
    :py:func:`make_forked_return<deltalanguage.data_types.make_forked_return>`
    beforehand, then the outputs can be send out in any configuration:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> TwoIntsT, TwoIntsC = dl.make_forked_return({'x': int, 'y': int})

        >>> @dl.Interactive(in_params={"a": int}, out_type=TwoIntsT)
        ... def baz(node: PythonNode):
        ...     for i in range(10):
        ...         a = node.receive("a")
        ...         if a%3 == 0:
        ...             node.send(TwoIntsC(x=a, y=None))
        ...         elif a%3 == 1:
        ...             node.send(TwoIntsC(x=None, y=a))
        ...         else:
        ...             node.send(TwoIntsC(x=a, y=a))
    """
    if len(in_params) == 0 and out_type == Void:
        raise DeltaIOError('Interactive node must have either an input '
                           'or an output. Otherwise it may freeze '
                           'the runtime simulator.')

    def decorator(a_func: Callable[[PythonNode], None]):
        proc = InteractiveProcess(a_func,
                                  in_params,
                                  out_type,
                                  name or a_func.__name__,
                                  in_port_size,
                                  lvl)
        return proc
    return decorator
