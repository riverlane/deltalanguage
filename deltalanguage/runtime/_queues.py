from copy import deepcopy
import logging
from queue import Empty, Queue
from typing import Any

from deltalanguage.wiring import OutPort
from deltalanguage.logging import make_logger
from deltalanguage._utils import QueueMessage


class Flusher:
    """Empty class is passed down queues to release a blockage."""
    pass


class DeltaQueue(Queue):
    """Queue that communicate messages between a sending
    :py:class:`OutPort<deltalanguage.wiring.OutPort>` and a receiving
    :py:class:`InPort<deltalanguage.wiring.InPort>`.

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
        blocking nodes at ``put`` methods as they are full. The simulator
        interrupts this at this periodicity (in seconds) and checks if
        stopping is needed.

    .. note::
        :py:class:`DeltaPySimulator<deltalanguage.runtime.DeltaPySimulator>`
        performs all required splitting of data on the background
        (if required).
        This is not a user-facing class and we leave further comments away
        from the documentation.

    Attributes
    ----------
    optional : bool
        Identify if the corresponding
        :py:class:`InPort<deltalanguage.wiring.InPort>` of the receiving node
        requires a message from this queue or it's optional.
        If ``False`` and nothing is sent down this queue, the caller will use
        ``Queue.get()`` with block and wait.
    index : Union[str, None]
        For ``ForkedReturn`` this stores the name of
        :py:class:`OutPort<deltalanguage.wiring.OutPort>` providing
        messages for this queue. Otherwise it's ``None``.
    """

    def __init__(self,
                 out_port: OutPort,
                 maxsize: int = 16,
                 queue_interval: float = 1.0):
        super().__init__(maxsize=maxsize)
        self._src = out_port
        self._log = make_logger(logging.WARNING,
                                f"Queue {out_port.port_name}")
        self.queue_interval = queue_interval
        self.optional = out_port.destination.is_optional

        self.index = None
        if out_port.port_name.n_index is not None:
            self.index = out_port.port_name.n_index

    def index_item(self, item):
        """Check if only one attribute of the given item should be sent, and
        if so, perform the indexing.
        This is what actually does the output forking.
        """
        if self.index is not None:
            msg = item.msg
            to_put_msg = msg[msg._fields.index(self.index)]
            to_put = QueueMessage(msg=to_put_msg, clk=item.clk)
        else:
            to_put = item
        assert isinstance(to_put, QueueMessage)
        return to_put

    def get(self, block=True):
        item = Queue.get(self, block)
        # I'm not sure we should need this...
        if not isinstance(item, QueueMessage):
            raise TypeError(
                f"Expected QueueMessage object, but object {item} is in queue")
        assert isinstance(item, QueueMessage)
        return item

    def put(self, item, block=True, timeout=None):
        """Add an item to a queue, performing the indexing if it applies.

        .. warning::
            If the value to be added is None, it is ignored.
        """
        if not isinstance(item, QueueMessage):
            raise TypeError(f"Only values of type QueueMessage should be "
                            f"sent in a df queue.\nitem: {item}")
        to_put = self.index_item(item)
        if to_put.msg is not None:
            if timeout is None:
                Queue.put(self, to_put, block, timeout=self.queue_interval)
            else:
                Queue.put(self, to_put, block, timeout)

    def get_or_none(self):
        """If there is no item in the queue, return None."""
        try:
            item = self.get(block=False)
            if item is None:  # I'm not sure we should need this...
                item = QueueMessage(None, clk=0)
        except Empty:
            item = QueueMessage(None, clk=0)  # none from the start of time

        assert isinstance(item, QueueMessage)
        return item

    def flush(self):
        """Unblock any thread waiting for this queue."""
        if self.empty():
            Queue.put(self, QueueMessage(Flusher(), clk=-1))


class ConstQueue(DeltaQueue):
    """An imitation queue created at the output of
    :py:class:`PyConstNode<deltalanguage.wiring.PyConstNode>`.

    A deepcopy of the message from this queue is passed to the receiving node
    and it is _not_ removed from the queue, thus the next time the receiving
    node ask for the input the same message will be produced without
    re-evaluation of the node this message originated from.

    Parameters
    ----------
    out_port : OutPort
        Output port for which this queue is created.

    Attributes
    ----------
    saved_value : Any
        The message itself.


    .. warning::
        A common misconception about this queue is that the message is passed
        to the receiving node only once, this is not true. You should think
        about an instance of this queue as a continuous stream of identical
        messages. For instance, if the receiving node has only one non-optional
        input from this queue it will be passed to that node at every iteration.
    """

    def __init__(self, out_port):
        super().__init__(out_port, maxsize=1)
        self.saved_value = None

    def put(self, item, block=True, timeout=None):
        if not isinstance(item, QueueMessage):
            raise TypeError(
                f"Only values of type QueueMessage should be sent in a df queue.\nitem: {item}")

        if self.saved_value is None:
            val = self.index_item(item)
            if val.msg is not None:
                self.saved_value = val
                # emtpy will now be false
                Queue.put(self, self.saved_value, block, timeout)
            elif not self.optional:
                raise ValueError("None cannot be pushed to "
                                 + "non-optional ConstQueue.")
        else:
            raise ValueError("Put to already populated ConstQueue.")

    def get(self, block=True):
        if self.empty():
            raise Empty()
        return deepcopy(self.saved_value)

    def flush(self):
        """Overriden flush that does nothing if the queue is already populated.
        """
        if self.empty():
            Queue.put(self, QueueMessage(msg=Flusher()))
