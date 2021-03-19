"""Testing queues work."""

from queue import Empty, Full, Queue
import unittest

from deltalanguage.data_types import DOptional, DInt
from deltalanguage.runtime import ConstQueue, DeltaQueue
from deltalanguage.runtime._queues import Flusher
from deltalanguage._utils import NamespacedName, QueueMessage
from deltalanguage.wiring import InPort, OutPort

from deltalanguage.test._utils import TwoInts, TwoIntsT


class TestDeltaQueue(unittest.TestCase):
    """Base test class for testing DeltaQueue and a ConstQueue attached to
    an out port leading to either an obligatory or an optional in port.

    In this case queues are attached to a port with a non-forker output.
    """

    def setUp(self):
        # obligatory and optional ports
        out_port_obl = OutPort(
            NamespacedName("port_name", None),
            DInt(),
            InPort(NamespacedName("port_name", None),
                   DInt(), None, 0),
            None
        )
        out_port_opt = OutPort(
            NamespacedName("port_name", None),
            DInt(),
            InPort(NamespacedName("port_name", None),
                   DOptional(DInt()), None, 0),
            None
        )

        # 4 types of queues
        self.delta_queue_obl = DeltaQueue(out_port_obl)
        self.delta_queue_opt = DeltaQueue(out_port_opt)
        self.const_queue_obl = ConstQueue(out_port_obl)
        self.const_queue_opt = ConstQueue(out_port_opt)

        # test messages
        self.msg1 = QueueMessage(1)
        self.msg2 = QueueMessage(2)
        self.msg_with_none = QueueMessage(None)
        self.msg_unpackable = QueueMessage("abcde")

        # these messages should be received
        self.msg1_answer = QueueMessage(1)
        self.msg2_answer = QueueMessage(2)
        self.msg_with_none_answer = QueueMessage(None)

    def test_put(self):
        """The queues accept at least one message."""
        for q in (self.delta_queue_obl, self.delta_queue_opt,
                  self.const_queue_obl, self.const_queue_opt):
            q.put(self.msg1)

    def test_put_multiple(self):
        """DeltaQueue accepts multiple messages,
        ConstQueue can accept only one message and raises Full."""
        for q in (self.delta_queue_obl, self.delta_queue_opt):
            for _ in range(10):
                q.put(self.msg1)

        for q in (self.const_queue_obl, self.const_queue_opt):
            q.put(self.msg1)
            with self.assertRaises(Full):
                q.put(self.msg2)

    def test_put_none(self):
        """Test that None is not inserted the queues."""
        for q in (self.delta_queue_obl, self.delta_queue_opt):
            for _ in range(10):
                q.put(self.msg_with_none)
            self.assertEqual(q.empty(), True)

        # also check cache for ConstQueue
        for q in (self.const_queue_obl, self.const_queue_opt):
            for _ in range(10):
                q.put(self.msg_with_none)
            self.assertEqual(q.empty(), True)
            self.assertTrue(q._saved_value == None)

    def test_put_to_full(self):
        """What happens when the queue is already full."""
        # ConstQueue raises Full, it should never happen.
        for q in (self.const_queue_obl, self.const_queue_opt):
            q.put(self.msg1)
            with self.assertRaises(Full):
                q.put(self.msg2)

        # DeltaQueue is blocking and then raises Full after timeout
        for q in (self.delta_queue_obl, self.delta_queue_opt):
            for _ in range(16):
                q.put(self.msg1)
            with self.assertRaises(Full):
                q.put(self.msg2, timeout=0.1)
            with self.assertRaises(Full):
                q.put(self.msg2)

    def test_put_queue_message_exception(self):
        """Test that TypeError is raised if input is not QueueMessage."""
        for q in (self.delta_queue_obl, self.delta_queue_opt,
                  self.const_queue_obl, self.const_queue_opt):
            with self.assertRaises(TypeError):
                q.put(self.msg1.msg)

    def test_put_unpackable_message(self):
        """Test that TypeError is raised if input cannot be packed."""
        for q in (self.delta_queue_obl, self.delta_queue_opt,
                  self.const_queue_obl, self.const_queue_opt):
            with self.assertRaises(TypeError):
                q.put(self.msg_unpackable)

    def test_get(self):
        """The queues always return one message."""
        for q in (self.delta_queue_obl, self.delta_queue_opt,
                  self.const_queue_obl, self.const_queue_opt):
            q.put(self.msg1)
            self.assertEqual(q.get(), self.msg1_answer)

    def test_get_multiple(self):
        """Order of messages is preserved,
        ConstQueue returns the same message.
        """
        for q in (self.delta_queue_obl, self.delta_queue_opt):
            for _ in range(5):
                q.put(self.msg1)
                q.put(self.msg2)

            for _ in range(5):
                self.assertEqual(q.get(), self.msg1_answer)
                self.assertEqual(q.get(), self.msg2_answer)

        for q in (self.const_queue_obl, self.const_queue_opt):
            q.put(self.msg1)
            for _ in range(5):
                self.assertEqual(q.get(), self.msg1_answer)

    def test_get_from_empty(self):
        """Getting from empty queues, details are in comments."""
        # all optional empty queues return None without blocking
        for q in (self.delta_queue_opt, self.const_queue_opt):
            self.assertEqual(q.get(), self.msg_with_none_answer)

        # non-optional empty DeltaQueue is blocking and then raises Empty
        # after timeout
        with self.assertRaises(Empty):
            self.delta_queue_obl.get(timeout=0.1)

        # non-optional empty ConstQueue raises Empty without blocking
        with self.assertRaises(Empty):
            self.const_queue_obl.get()

    def test_flush_empty(self):
        """If any empty queue is flushed then a message with Flusher is added.
        """
        for q in (self.delta_queue_obl, self.delta_queue_opt,
                  self.const_queue_obl, self.const_queue_opt):
            q.flush()
            self.assertIsInstance(q.get().msg, Flusher)

    def test_flush_non_empty(self):
        """If any non-empty queue is flushed then nothing happens."""
        for q in (self.delta_queue_obl, self.delta_queue_opt,
                  self.const_queue_obl, self.const_queue_opt):
            q.put(self.msg1)
            q.flush()
            self.assertEqual(q.get(), self.msg1_answer)

        # DeltaQueue becomes empty
        for q in (self.delta_queue_obl, self.delta_queue_opt):
            self.assertEqual(q.empty(), True)

        # ConstQueue keeps holding the cached message
        for q in (self.const_queue_obl, self.const_queue_opt):
            self.assertEqual(q.get(), self.msg1_answer)


class TestDeltaQueueForkedReturn(TestDeltaQueue):
    """In this case queues are attached to a port with a forker output."""

    def setUp(self):
        # obligatory and optional ports
        out_port_obl = OutPort(
            NamespacedName("port_name", "x"),
            TwoIntsT,
            InPort(NamespacedName("port_name", None),
                   DInt(), None, 0),
            None
        )
        out_port_opt = OutPort(
            NamespacedName("port_name", "x"),
            TwoIntsT,
            InPort(NamespacedName("port_name", None),
                   DOptional(DInt()), None, 0),
            None
        )

        # 4 types of queues
        self.delta_queue_obl = DeltaQueue(out_port_obl)
        self.delta_queue_opt = DeltaQueue(out_port_opt)
        self.const_queue_obl = ConstQueue(out_port_obl)
        self.const_queue_opt = ConstQueue(out_port_opt)

        # test messages
        self.msg1 = QueueMessage(TwoInts(1, 20))
        self.msg2 = QueueMessage(TwoInts(2, 30))
        self.msg_with_none = QueueMessage(TwoInts(None, 20))
        self.msg_unpackable = QueueMessage(TwoInts("abcde", 20))

        # these messages should be received
        self.msg1_answer = QueueMessage(1)
        self.msg2_answer = QueueMessage(2)
        self.msg_with_none_answer = QueueMessage(None)


if __name__ == "__main__":
    unittest.main()
