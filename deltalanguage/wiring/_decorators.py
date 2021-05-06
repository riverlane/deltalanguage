"""User facing decorators for building DeltaGraph nodes."""

from __future__ import annotations
from functools import wraps
import logging
from typing import (TYPE_CHECKING,
                    Callable,
                    List,
                    Optional,
                    Tuple,
                    Type)

from ._delta_graph import DeltaGraph
from ._node_classes.real_nodes import PythonNode
from ._node_templates import NodeTemplate, InteractiveBodyTemplate

if TYPE_CHECKING:
    from deltalanguage.wiring import Latency


def DeltaBlock(
    outputs: List[Tuple[str, Type]] = None,
    template: NodeTemplate = None,
    allow_const: bool = True,
    node_key: Optional[str] = None,
    name: str = None,
    in_port_size: int = 0,
    latency: Latency = None,
    lvl: int = logging.ERROR,
    tags: List[str] = None
):
    """Decorator to turn a function to a block for use in
    :py:class:`DeltaGraph`.

    If called in the context of :py:class:`DeltaGraph` it will
    return a stateless node, which means that the output of such a node is
    fully determined by its inputs; exactly as it happens in functional
    programming.

    The node is evaluated when all compulsory inputs are provided.
    By default each input is compulsory, in order to make it optional use
    :py:class:`Optional<deltalanguage.data_types.Optional>` wrapper.

    .. warning::
        If a node does not have compulsory inputs then it will be evaluated
        continuesly and this can significantly slow down a runtime simulator.
        If node does not have optional inputs consider using
        ``allow_const=True`` to improve performance.

    Parameters
    ----------
    outputs : List[Tuple[str, Type]]
        The types and names of the outputs for the node to be made.
    template : NodeTemplate
        Associate this node constructor with this specfied existing node
        template rather than a newly created one.
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
        ...     s.save_and_exit(foo_out)

        >>> dl.DeltaPySimulator(graph).run()
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
        ...     s.save_and_exit(bar(a=9, b=9))

        >>> dl.DeltaPySimulator(graph).run()
        saving 81

    Nodes can send multiple outputs by specifying the names and types of these
    outputs in the decorator. When doing this, no output type annotation is
    needed.

    .. code-block:: python

        >>> @dl.DeltaBlock(outputs=[('x', int), ('y', int)])
        ... def baz(a: int, b: int):
        ...     return a+5, a*b

    We can then refer to the different outputs of this node using indexing,
    where the index matches the name of the output as specified in the
    decorator.

    .. code-block:: python

        >>> with dl.DeltaGraph() as graph_2:
        ...     baz_out = baz(10, 2)
        ...     s.save_and_exit(bar(baz_out.x, baz_out.y))

        >>> dl.DeltaPySimulator(graph_2).run()
        saving 300

    You can use indexing to reference the output of a node with only one
    output, its default name will be ``output``. However, you can also
    specify and use another name, by setting the decorator ``outputs``
    paramater with just a single output.
    """
    def decorator(func):
        _outputs = outputs if outputs is not None else []
        my_template = NodeTemplate.merge_deltablock(template,
                                                    _outputs,
                                                    func,
                                                    allow_const,
                                                    node_key,
                                                    name or func.__name__,
                                                    in_port_size,
                                                    latency,
                                                    lvl,
                                                    tags)

        @wraps(func)
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
                # There is currently an active DeltaGraph so use template
                return my_template.call(*args, **kwargs)
            else:
                # No DeltaGraph active so evaluate function as usual
                return func(*args, **kwargs)
        decorated.template = my_template
        return decorated
    return decorator


def DeltaMethodBlock(
    outputs: List[Tuple[str, Type]] = None,
    template: NodeTemplate = None,
    name: str = None,
    node_key: Optional[str] = None,
    in_port_size: int = 0,
    latency: Latency = None,
    lvl: int = logging.ERROR,
    tags: List[str] = None
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
    :py:class:`Optional<deltalanguage.data_types.Optional>` wrapper.

    .. warning::
        If a node does not have compulsory inputs then it will be evaluated
        continuesly and this can significantly slow down a runtime simulator.

    Parameters
    ----------
    outputs : List[Tuple[str, Type]]
        The types and names of the outputs for the node to be made.
    template : NodeTemplate
        Associate this node constructor with this specfied existing node
        template rather than a newly created one.
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
        ...     s.save_and_exit(my_obj.bar(5))

        >>> dl.DeltaPySimulator(graph).run()
        saving 15

    However if the internal state of the object changes (before or during),
    the result will change:

    .. code-block:: python

        >>> my_obj.x = 15

        >>> dl.DeltaPySimulator(graph).run()
        saving 20

    Nodes can also have multiple inputs and outputs exactly as
    :py:class:`DeltaBlock`.
    """

    def decorator(func):
        _outputs = outputs if outputs is not None else []
        my_template = NodeTemplate.merge_deltamethod(template,
                                                     _outputs,
                                                     func,
                                                     node_key,
                                                     name or func.__name__,
                                                     in_port_size,
                                                     latency,
                                                     lvl,
                                                     tags)

        @wraps(func)
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
                # there is currently an active DeltaGraph so use template
                return my_template.call(obj, *args, **kwargs)
            else:
                # No DeltaGraph active so evaluate function as usual
                return func(obj, *args, **kwargs)
        decorated.template = my_template
        return decorated
    return decorator


def Interactive(
    inputs: List[Tuple[str, Type]] = None,
    outputs: List[Tuple[str, Type]] = None,
    template: NodeTemplate = None,
    name: str = None,
    in_port_size: int = 0,
    latency: Latency = None,
    lvl: int = logging.ERROR,
    tags: List[str] = None
) -> Callable[..., InteractiveBodyTemplate]:
    """Decorator to turn a function of a special type (see examples)
    to an interactive node for use in :py:class:`DeltaGraph`.

    The function used with this decorator is not meant to be used on its own
    (i.e. outside of the graph) in contrast with
    :py:class:`DeltaBlock` and :py:class:`DeltaMethodBlock`.

    The types of inputs and outputs have to be defined using ``inputs`` and
    ``outputs``. By default each input is compulsory, in order to make it
    optional use :py:class:`Optional<deltalanguage.data_types.Optional>`
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
    inputs : List[Tuple[str, Type]]
        The types and names of the in parameters to the node to be made.
    outputs : List[Tuple[str, Type]]
        The types and names of the outputs for the node to be made.
    template : NodeTemplate
        Associate this node constructor with this specfied existing node
        template rather than a newly created one.
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

        >>> @dl.Interactive([("a", int), ("b", int)], [('output', int)])
        ... def foo(node: dl.PythonNode):
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
        ...     s.save_and_exit(foo.call(a=4, b=5))

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 200

    Here is the case when inputs are read independently:

    .. code-block:: python

        >>> @dl.Interactive([("a", int), ("b", int)], [('output', int)])
        ... def bar(node: dl.PythonNode):
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
        ...     s.save_and_exit(bar.call(a=4, b=5))

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving -5

    Nodes can send multiple outputs by specifying the names and types of these
    outputs in the decorator. Keywords can be used in the ``send`` method to
    clearly specify the multiple output values.

    .. code-block:: python

        >>> @dl.Interactive([("a", int), ("b", int)], [('x', int), ('y', int)])
        ... def bar(node: dl.PythonNode):
        ...     internal_memory = 0
        ...
        ...     for i in range(10):
        ...         if i%2 == 0:
        ...             internal_memory += node.receive("a")
        ...         else:
        ...             internal_memory -= node.receive("b")
        ...
        ...     node.send(x=internal_memory, y=internal_memory*2)
    """
    def decorator(func: Callable[[PythonNode], None]):
        _outputs = outputs if outputs is not None else []
        _inputs = inputs if inputs is not None else []
        proc = NodeTemplate.merge_interactive(template,
                                              func,
                                              _inputs,
                                              _outputs,
                                              name or func.__name__,
                                              in_port_size,
                                              latency,
                                              lvl,
                                              tags)
        return proc
    return decorator
