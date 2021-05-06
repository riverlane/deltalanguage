from copy import deepcopy
import logging
from queue import Empty, Full, Queue

from deltalanguage.wiring import OutPort
from deltalanguage.logging import make_logger
from deltalanguage._utils import QueueMessage


class Flusher:
    """Empty class is passed down queues to release a blockage."""
    pass


class DeltaQueue(Queue):
    """Queue class that communicate messages between nodes in
    :py:class:`DeltaPySimulator<deltalanguage.runtime.DeltaPySimulator>`.

    The object connects corresponding I/O ports.

    .. note::
        :py:class:`DeltaPySimulator<deltalanguage.runtime.DeltaPySimulator>`
        performs all required splitting of data on the background
        (if required).

    Parameters
    ----------
    out_port : OutPort
        Output port for which this queue is created.
    maxsize : int
        If maxsize is <= 0, the queue size is infinite.
        The default value 16 is chosen in analogy with ``sc_fifo`` in SystemC,
        this means that the Python GIL will be forced to run another node's
        thread once the queue is full, thus it will prevent blockage.
    queue_interval : float
        When the simulation is called to stop, some of the queues might be
        blocking nodes at ``put`` methods as they are full.
        :py:class:`DeltaPySimulator<deltalanguage.runtime.DeltaPySimulator>`
        interrupts this at this periodicity (in seconds) and checks if
        stopping is needed.

    Attributes
    ----------
    optional : bool
        Identify if the corresponding
        :py:class:`InPort<deltalanguage.wiring.InPort>` of the receiving node
        requires a message from this queue or it's optional.
        If ``False`` and nothing is sent down this queue, the caller will use
        ``Queue.get()`` with block and wait.
    """

    def __init__(self,
                 out_port: OutPort,
                 maxsize: int = 16,
                 queue_interval: float = 1.0):
        super().__init__(maxsize=maxsize)
        self._src = out_port
        self._log = make_logger(logging.WARNING,
                                f"Queue {out_port.name}")
        self._queue_interval = queue_interval
        self.optional = out_port.destination.is_optional

        self._type = out_port.port_type

    def get(self, block=True, timeout=None) -> QueueMessage:
        """If the queue is optional and empty return ``None``,
        otherwise return the item.
        """
        if self.optional and self.empty():
            return QueueMessage(None, clk=0)

        item = Queue.get(self, block=block, timeout=timeout)

        return item

    def _delta_put(self, item: QueueMessage, block=True, timeout=None):
        """Add item to this queue.

        ``None`` is not added to the queue.

        If the queue is full, a Full exception is raised after a timeout so
        that the node pushing to it becomes unblocked to check for an exit
        signal.
        """
        if not isinstance(item, QueueMessage):
            raise TypeError("Only QueueMessage objects can be put on queues")

        if item.msg is not None:
            if not self._type.is_packable(item.msg):
                raise TypeError(
                    f"Message {item.msg} cannot be packed into {self._type}")
            if timeout is None:
                Queue.put(self, item, block, timeout=self._queue_interval)
            else:
                Queue.put(self, item, block, timeout=timeout)

    def put(self, item: QueueMessage, block=True, timeout=None):
        """Add an item to a queue.

        .. warning::
            If ``item.msg == None``, it is not added to the queue.
        """
        self._delta_put(item, block, timeout)

    def flush(self):
        """Unblock any thread waiting for this queue."""
        if self.empty():
            Queue.put(self, QueueMessage(Flusher(), clk=-1))


class ConstQueue(DeltaQueue):
    """An imitation queue created at the output of
    :py:class:`PyConstBody<deltalanguage.wiring.PyConstBody>`.

    A deepcopy of the message from this queue is passed to the receiving node
    and it is _not_ removed from the queue, thus the next time the receiving
    node ask for the input the same message will be produced without
    re-evaluation of the node this message originated from.

    Parameters
    ----------
    out_port : OutPort
        Output port for which this queue is created.


    .. warning::
        A common misconception about this queue is that the message is passed
        to the receiving node only once, this is not true. You should think
        about an instance of this queue as a continuous stream of identical
        messages. For instance, if the receiving node has only one non-optional
        input from this queue it will be passed to that node at every iteration.
    """

    def __init__(self, out_port):
        super().__init__(out_port, maxsize=1)
        self._saved_value = None

    def put(self, item: QueueMessage, block=True, timeout=None):
        """Overwrite ``DeltaQueue.put``."""
        if self._saved_value is None:
            self._delta_put(item, block, timeout)

            # only non-None is saved
            if item.msg is not None:
                self._saved_value = item
        else:
            raise Full("Put to already populated ConstQueue.")

    def get(self) -> QueueMessage:
        """Overwrite ``DeltaQueue.get``, block and timeout are unavailable."""
        if self.empty():
            if self.optional:
                return QueueMessage(None, clk=0)

            raise Empty

        return deepcopy(self._saved_value)

    def flush(self):
        """Overwrite ``DeltaQueue.flush``"""
        if self.empty():
            self._saved_value = QueueMessage(Flusher(), clk=-1)
            Queue.put(self, self._saved_value)
