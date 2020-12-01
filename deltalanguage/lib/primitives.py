"""
Primitives for examples, tests, and just general use.
"""
from copy import deepcopy
from typing import Callable, List

from ..data_types import delta_type, NoMessage
from ..runtime import DeltaRuntimeExit
from ..wiring import (DeltaMethodBlock,
                      Interactive,
                      PyInteractiveNode)


def make_interactive_generator(val, reps=1, verbose=False):
    """Returns a state generator implemented via
    :py:class:`PyInteractiveNode<deltalanguage.wiring.PyInteractiveNode>`.

    This generator is useful for checking the robustness of the graph vs
    multiple messages and soak testing in general. Also used for making a
    testbench for a node under design.

    .. todo:: Add an example with a testbench.

    Parameters
    ----------
    val : object
        The output value of the generator. Its Deltaflow type is recognized
        automatically by
        :py:class:`delta_type<deltalanguage.data_types.delta_type>`.
    reps : int
        Number of emitted messenger.
    verbose : bool
        If ``True`` prints the status.

    Examples
    --------
    In this example the created generator produces 10 messages containing
    ``True``. Note that the generator should be used in the same way as an
    interactive node:

    .. code-block:: python

        generator = make_interactive_generator(True, 10)
        with DeltaGraph() as graph:
            gen_bools = generator.call()
            ...
    """
    @Interactive({}, delta_type(val))
    def generator(node: PyInteractiveNode):
        for _ in range(reps):
            if verbose:
                print(f"sending {val}")

            node.send(val)

    return generator


class IntListSender:
    """Sends a list of integers as individual messages.

    This generator is useful for checking the robustness of the graph vs
    multiple messages and soak testing in general. Also used for making a
    testbench for a node under design.

    Parameters
    ----------
    to_send : List[int]
        Integers to send.


    .. todo:: Add an example with a testbench.


    Examples
    --------
    In this example the following integers send as individual messages:

    .. code-block:: python

        sender = IntListSender([1, 3, 4, 9, 0, -1, 8])
        with DeltaGraph() as graph:
            gen_ints = sender.send_all()
            ...
    """

    def __init__(self, to_send: List[int]):
        self.my_list = deepcopy(to_send)
        self.my_list.reverse()

    @DeltaMethodBlock()
    def send_all(self) -> int:
        """Sender method.

        Returns
        -------
        int
        """
        if self.my_list:
            return self.my_list.pop()


class StateSaver:
    """Stores all input state via various methods.

    This is useful for debugging and testing purposes, in particular
    users can store and benchmark data transmitted between nodes.
    Also used for making a testbench for a node under design.


    Parameters
    ----------
    condition : Callable
        Used for the conditional blocks, see examples.
    verbose : bool
        If ``True`` prints a status on node's activation.


    .. todo:: Add an example with a testbench and ``pass_*`` methods.


    Examples
    --------
    In this graph a single message is saved via :py:meth:`StateSaver.save`:

    .. code-block:: python

        s = StateSaver()
        with DeltaGraph() as graph:
            s.save(42)

    Same as :py:meth:`StateSaver.save` but followed by the formal graph exit:

    .. code-block:: python

        s = StateSaver()
        with DeltaGraph() as graph:
            s.save_and_exit(42)

    Same as :py:meth:`StateSaver.save_and_exit` but if a condition is
    fulfilled (in this case it is):

    .. code-block:: python

        s = StateSaver(condition=lambda x: x>10)
        with DeltaGraph() as graph:
            s.save_and_exit_if(42)

    Same as :py:meth:`StateSaver.save` but also returns a status, which
    can be used to trigger futher actions in the graph:

    .. code-block:: python

        s = StateSaver()
        with DeltaGraph() as graph:
            status = s.save_and_ack(42)
            ...
    """

    def __init__(self,
                 condition=None,
                 verbose=False):
        self.reset()
        self.condition = condition
        self.verbose = verbose

    def reset(self):
        """Remove all stored states."""
        self.saved = []

    def store(self, val):
        """Helper method used for storing."""
        if self.verbose:
            print(f"saving {val}")
        self.saved.append(val)

    @DeltaMethodBlock()
    def save(self, val: object) -> NoMessage:
        """Saves input of any type.

        Parameters
        ----------
        val : object
            Incoming message.
        """
        self.store(val)

    @DeltaMethodBlock()
    def save_and_exit(self, val: object) -> NoMessage:
        """Saves input of any type and exit.

        Parameters
        ----------
        val : object
            Incoming message.
        """
        self.store(val)
        raise DeltaRuntimeExit

    @DeltaMethodBlock()
    def save_and_exit_if(self, val: object) -> NoMessage:
        """Saves input of any type and exit if a condition is fulfilled.

        Parameters
        ----------
        val : object
            Incoming message.
        """
        self.store(val)
        assert self.condition is not None, "Undefined condition"
        if self.condition(val):
            raise DeltaRuntimeExit

    @DeltaMethodBlock()
    def save_and_ack(self, val: object) -> bool:
        """Saves input of any type and return an acknowledgement.

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

    @DeltaMethodBlock()
    def pass_object(self, val: object) -> object:
        self.store(val)
        return val

    @DeltaMethodBlock()
    def pass_int(self, val: int) -> int:
        self.store(val)
        return val

    @DeltaMethodBlock()
    def pass_int_if(self, val: int) -> int:
        self.store(val)
        assert self.condition is not None, "Undefined condition"
        if self.condition(val):
            return val
        else:
            raise NoMessage

    @DeltaMethodBlock()
    def pass_bool(self, val: bool) -> bool:
        self.store(val)
        return val
