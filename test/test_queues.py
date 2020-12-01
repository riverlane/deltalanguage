"""Testing that the correct type of queues is created and how they work."""

from queue import Empty, Queue
import unittest

from test._utils import TwoInts, simple_graph_forked

from deltalanguage.data_types import DOptional, DInt
from deltalanguage.runtime import ConstQueue, DeltaQueue
# Users should not use QueueMessage
from deltalanguage._utils import NamespacedName, QueueMessage
from deltalanguage.wiring import InPort, OutPort


class TestConstQueue(unittest.TestCase):

    def setUp(self):
        """Construct a forked graph and queue ONLY the first values of the
        forked output."""
        graph = simple_graph_forked()
        self.out_port = graph.nodes[0].out_ports[0]
        self.queue = ConstQueue(self.out_port)

    def test_instance(self):
        """Test correct inheritance."""
        self.assertIsInstance(self.queue, Queue)
        self.assertIsInstance(self.queue, DeltaQueue)
        self.assertIsInstance(self.queue, ConstQueue)

    def test_put(self):
        """Test that insertion works."""
        self.queue.put(QueueMessage(TwoInts(3, 2)))
        self.assertEqual(self.queue.saved_value, QueueMessage(3))

    def test_second_put(self):
        """Second insertion to const Queue should throw error."""
        self.queue.put(QueueMessage(TwoInts(3, 2)))
        with self.assertRaises(ValueError):
            self.queue.put(QueueMessage(TwoInts(4, 5)))

    def test_get(self):
        """Test that getting works."""
        self.queue.put(QueueMessage(TwoInts(3, 2)))
        val = self.queue.get()
        self.assertEqual(val.msg, 3)

    def test_second_get(self):
        """Test getting a second time."""
        self.queue.put(QueueMessage(TwoInts(3, 2)))
        val = self.queue.get()
        self.assertEqual(val.msg, 3)
        val = self.queue.get()
        self.assertEqual(val.msg, 3)

    def test_empty_get(self):
        """Test that getting from an emtpy queue with no block raises error."""
        with self.assertRaises(Empty):
            self.queue.get(block=False)

    def test_put_none_nonoptional(self):
        """Test that putting None on non-optional ConstQueue raises error."""
        with self.assertRaises(ValueError):
            self.queue.put(QueueMessage(TwoInts(None, 3)))

    def test_put_none_optional(self):
        """Test that putting None on optional ConstQueue returns None."""
        out_port = OutPort(NamespacedName("port_name", None),
                           DInt(),
                           InPort(NamespacedName("port_name", None),
                                  DOptional(DInt()), None, 0),
                           None)
        queue = ConstQueue(out_port)
        queue.put(QueueMessage(None))
        self.assertEqual(queue.get_or_none().msg, None)


class TestDeltaQueue(unittest.TestCase):

    def setUp(self):
        """Construct a forked graph and queue ONLY the first values of the
        forked output."""
        graph = simple_graph_forked()
        self.out_port = graph.nodes[0].out_ports[0]
        self.queue = DeltaQueue(self.out_port)

    def test_instance(self):
        """Test correct inheritance."""
        self.assertIsInstance(self.queue, Queue)
        self.assertIsInstance(self.queue, DeltaQueue)
        self.assertNotIsInstance(self.queue, ConstQueue)

    def test_put(self):
        """Test that insertion works."""
        self.queue.put(QueueMessage(TwoInts(3, 2)))

    def test_second_put(self):
        """Second insertion to const Queue should throw error."""
        self.queue.put(QueueMessage(TwoInts(3, 2)))
        self.queue.put(QueueMessage(TwoInts(4, 5)))

    def test_get(self):
        """Test that getting works."""
        self.queue.put(QueueMessage(TwoInts(3, 2)))
        val = self.queue.get()
        self.assertEqual(val.msg, 3)

    def test_second_get(self):
        """Test that getting works."""
        self.queue.put(QueueMessage(TwoInts(3, 2)))
        self.queue.put(QueueMessage(TwoInts(4, 5)))
        val = self.queue.get()
        self.assertEqual(val.msg, 3)
        val = self.queue.get()
        self.assertEqual(val.msg, 4)

    def test_get_or_none(self):
        """Test that get_or_none works."""
        self.queue.put(QueueMessage(TwoInts(3, 2)))
        val = self.queue.get_or_none()
        self.assertEqual(val.msg, 3)
        val = self.queue.get_or_none()
        self.assertEqual(val.msg, None)
        val = self.queue.get_or_none()
        self.assertEqual(val.msg, None)

    def test_queue_message_exception(self):
        """Test that ValueError is raised if input is not QueueMessage."""
        with self.assertRaises(TypeError):
            self.queue.put(3)


if __name__ == "__main__":
    unittest.main()
