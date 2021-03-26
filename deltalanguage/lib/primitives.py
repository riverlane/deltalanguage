"""
Primitives for examples, tests, and just general use.
"""
import json
from copy import deepcopy
from typing import Callable, Iterable, Type, Union

from ..data_types import (BaseDeltaType, Void,
                          delta_type, make_forked_return,
                          Complex, Array, Record, Tuple)
from ..runtime import DeltaRuntimeExit
from ..wiring import (DeltaBlock,
                      DeltaMethodBlock,
                      Interactive,
                      PythonNode,
                      InteractiveBodyTemplate)


def make_generator(val: Union[object, Iterable],
                   reps: int = None,
                   verbose: bool = False) -> InteractiveBodyTemplate:
    """Used to create a generator node that
    produces a series of messages of the same data type.

    This generator is useful for checking the robustness of the graph vs
    multiple messages and soak testing in general. Also used for making a
    testbench for a node under design.

    Parameters
    ----------
    val : Union[object, Iterable]
        The output value(s) of the generator.
        Its Deltaflow type is recognized automatically by
        :py:class:`delta_type<deltalanguage.data_types.delta_type>`.
        See ``reps`` for explanation.
    reps : int
        Number of repeated messages.
        If ``reps`` is ``None`` then ``val`` must be iterable.
        If ``reps`` is an integer then `val` is sent out this number of times.
    verbose : bool
        If ``True`` prints the status.

    Examples
    --------
    In this example you can find a basic use of this function.
    Note that the generator should be used in the same way as an
    interactive node:

    .. code-block:: python

        >>> import deltalanguage as dl

        # Generate 5 integers
        >>> generator = dl.lib.make_generator(10, reps=5)

        # Receive 5 integers and send their sum
        >>> @dl.Interactive([("a", int)], int)
        ... def accumulator(node):
        ...     memory = []
        ...     for _ in range(5):
        ...         input = node.receive("a")
        ...         memory.append(input)
        ...     node.send(sum(memory))

        # Save the result
        >>> s = dl.lib.StateSaver(int, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     generator_out = generator.call()
        ...     accumulator_out = accumulator.call(a=generator_out)
        ...     s.save_and_exit(accumulator_out) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 50

    Also see this alternative usage:

    .. code-block:: python

        >>> generator = dl.lib.make_generator([1, 2, 3, 4, 5])

        >>> with dl.DeltaGraph() as graph:
        ...     generator_out = generator.call()
        ...     accumulator_out = accumulator.call(a=generator_out)
        ...     s.save_and_exit(accumulator_out) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 15
    """
    if reps is None:
        if not isinstance(val, Iterable):
            raise ValueError('If reps is None, then val must be iterable')

        elem_type = delta_type(val[0])
        if not all(elem_type == delta_type(e) for e in val):
            raise TypeError('Elements of val should be of the same type')

        vals_to_send = val
    else:
        elem_type = delta_type(val)
        vals_to_send = (deepcopy(val) for _ in range(reps))

    @Interactive([], elem_type)
    def generator(node: PythonNode):
        for v in vals_to_send:
            if verbose:
                print(f"sending {val}")

            node.send(v)

    return generator


def make_splitter(t: Union[Type, BaseDeltaType],
                  reps: int,
                  allow_const=True) -> Callable:
    """Used to create a splitter node, which sends multiple copies of
    incoming messages to different nodes via individual outputs.

    Names of output ports go in ascending order as ``out0``, ``out1``,
    ``out2``, etc. The total number of outputs is equal to ``reps``.

    Examples
    --------
    In this example you can find a basic use of this function:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> @dl.DeltaBlock()
        ... def adder(a: int, b: int) -> int:
        ...     return a + b

        >>> state_saver = dl.lib.StateSaver(int, verbose=True)

        >>> splitter = dl.lib.make_splitter(int, 2)

        >>> with dl.DeltaGraph() as graph:
        ...     splitter_out = splitter(10)
        ...     adder_out = adder(splitter_out.out0, splitter_out.out1)
        ...     state_saver.save_and_exit(adder_out) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 20
    """
    _SplitterT, _SplitterC = make_forked_return(
        {'out' + str(i): t for i in range(reps)}
    )

    @DeltaBlock(name="splitter", allow_const=allow_const)
    def _splitter(to_split: t) -> _SplitterT:
        return _SplitterC(*(deepcopy(to_split) for _ in range(reps)))

    return _splitter


class DeltaJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        obj_type = delta_type(obj)
        if isinstance(obj_type, Complex):
            return {"real": obj.real, "imaginary": obj.imag}
        elif isinstance(obj_type, (Array, Tuple)):
            return [self.default(o) for o in obj]
        elif isinstance(obj_type, Record):
            props = obj.__annotations__.keys()
            d = {p: self.default(getattr(obj, p)) for p in props}
            return d

        # Assume it's encodable; if we go back to JSONEncoder.default
        # this just returns a type error. See:
        # https://docs.python.org/3/library/json.html#json.JSONEncoder.default
        return obj


class StateSaver:
    """Class used for saving states via various methods.

    This is useful for debugging and testing purposes, in particular
    users can store and benchmark data transmitted between nodes.
    Also used for making a testbench for a node under design.

    Parameters
    ----------
    t : Union[Type, BaseDeltaType]
        Type of messages, by default object.
    condition : Callable
        Used for the conditional blocks, see examples.
    verbose : bool
        If ``True`` prints a status on node's activation.
    filename : str
        A filepath in which to save results, incrementally.

        If provided, this file will be appended with
        line-based JSON representation of the data saved.
        Note: The writing to the file is done when
        ``save`` is called is called.

    Examples
    --------
    In this graph a single message is saved via ``save``:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> s = dl.lib.StateSaver(int, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     s.save(42) # doctest:+ELLIPSIS
        save...

    Same as ``save`` but followed by the formal graph exit:

    .. code-block:: python

        >>> with dl.DeltaGraph() as graph:
        ...     s.save_and_exit(42) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 42

    Same as ``save_and_exit`` but if a condition is
    fulfilled (in this case it is):

    .. code-block:: python

        >>> s = dl.lib.StateSaver(int, condition=lambda x: x>10, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     s.save_and_exit_if(42) # doctest:+ELLIPSIS
        save_and_exit_if...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 42

    Same as ``save`` but also returns a status, which
    can be used to trigger futher actions in the graph:

    .. code-block:: python

        >>> gen = dl.lib.make_generator([42])
        >>> s0 = dl.lib.StateSaver(int, verbose=True)
        >>> s1 = dl.lib.StateSaver(bool, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     status = s0.save_and_ack(gen.call())
        ...     s1.save_and_exit(status) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 42
        saving True

    Also we can just save a message on passing:

    .. code-block:: python

        >>> gen = dl.lib.make_generator([42])
        >>> s0 = dl.lib.StateSaver(int, verbose=True)
        >>> s1 = dl.lib.StateSaver(int, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     message = s0.transfer(gen.call())
        ...     s1.save_and_exit(message) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 42
        saving 42

    And add a condition:

    .. code-block:: python

        >>> gen = dl.lib.make_generator([3, 8])
        >>> s0 = dl.lib.StateSaver(int, condition=lambda x: x%2==0,
        ...                        verbose=True)
        >>> s1 = dl.lib.StateSaver(int, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     message = s0.transfer_if(gen.call())
        ...     s1.save_and_exit(message) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 3
        saving 8
        saving 8

    .. warning::
        While ``t`` is optional, the default value of ``object`` should only
        be used for debugging in the Python simulator. Not specifying a type
        will cause execution in Deltasimulator to fail.
    """

    def __init__(self, t: Union[Type, BaseDeltaType] = object,
                 condition=None,
                 verbose=False,
                 filename=None):
        self.saved = []
        self.condition = condition
        self.verbose = verbose
        self.filename = filename

        @DeltaBlock(allow_const=False)
        def save(val: t) -> Void:
            """Save input of any type.

            Parameters
            ----------
            val : object
                Incoming message.
            """
            self.store(val)
        self.save = save

        @DeltaBlock(allow_const=False)
        def save_and_exit(val: t) -> Void:
            """Save input of any type and exit.

            Parameters
            ----------
            val : object
                Incoming message.
            """
            self.store(val)
            raise DeltaRuntimeExit
        self.save_and_exit = save_and_exit

        @DeltaBlock(allow_const=False)
        def save_and_exit_if(val: t) -> Void:
            """Save input of any type and exit if the condition is fulfilled.

            Parameters
            ----------
            val : object
                Incoming message.
            """
            self.store(val)
            assert self.condition is not None, "Undefined condition"
            if self.condition(val):
                raise DeltaRuntimeExit
        self.save_and_exit_if = save_and_exit_if

        @DeltaBlock(allow_const=False)
        def save_and_ack(val: t) -> bool:
            """Save input of any type and return an acknowledgement.

            Parameters
            ----------
            val : object
                Incoming message.

            Returns
            -------
            bool
            """
            self.store(val)
            return True
        self.save_and_ack = save_and_ack

        @DeltaBlock(allow_const=False)
        def transfer(val: t) -> t:
            """Save input of any type and return it.

            Parameters
            ----------
            val : object
                Incoming message.

            Returns
            -------
            object
            """
            self.store(val)
            return val
        self.transfer = transfer

        @DeltaBlock(allow_const=False)
        def transfer_if(val: t) -> t:
            """Save input of any type and return it if the contition
            is fulfilled.

            Parameters
            ----------
            val : object
                Incoming message.

            Returns
            -------
            object
            """
            self.store(val)
            assert self.condition is not None, "Undefined condition"
            if self.condition(val):
                return val
        self.transfer_if = transfer_if

    def reset(self):
        """Remove all stored states."""
        self.saved = []

    def store(self, val):
        """Helper method used for storing."""
        if self.verbose:
            print(f"saving {val}")
        self.saved.append(val)

        if self.filename is not None:
            with open(self.filename, "a") as f:
                f.write(json.dumps(val, cls=DeltaJsonEncoder) + "\n")
