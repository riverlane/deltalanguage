import logging
import threading
import time
import unittest

from test._utils import (TwoInts,
                         TwoIntsT,
                         add_non_const,
                         const_consumer,
                         return_1,
                         return_2)

from deltalanguage.data_types import as_delta_type, Void, DeltaIOError
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage._utils import QueueMessage
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  Interactive,
                                  PythonNode,
                                  placeholder_node_factory)


@DeltaBlock(name="node")
def int_to_str(n: int) -> str:
    return str(n)


@Interactive(in_params={"num": str}, out_type=int, name="blah")
def interactive_func(node: PythonNode):
    node.send(3)
    num = node.receive()["num"]
    num = int(num, base=10)
    node.send(num + 1)


@Interactive(in_params={"num": int}, out_type=int)
def forward(node: PythonNode):
    for _ in range(10):
        num = node.receive("num")
        node.send(num)
    raise DeltaRuntimeExit


@Interactive(in_params={'num': int}, out_type=TwoIntsT)
def add_until_10(node: PythonNode):
    """Sends num on the left port until it is greater than 10, then sends it
    on the right port.
    """
    num = 1
    while num < 10:
        node.send(TwoInts(num, None))
        num = node.receive()["num"]
    node.send(TwoInts(None, num))


class InteractiveNodeGeneralTest(unittest.TestCase):
    """Unsorted testes of interactive nodes."""

    def test_interactive_node_without_io(self):
        """Interactive node must have I/O. 

        We chose this rule because runtime simulators,
        in particular the Python GIL, wouldn't know when to
        interrupt this node simulation.

        In order to allow such nodes we need to change the simulation strategy.
        """

        with self.assertRaises(DeltaIOError):
            @Interactive({}, Void)
            def bar(node):
                while True:
                    pass

    def test_interactive_node_without_ports(self):
        """An interactive node with I/O can be just forgotten during graph
        construction. We check that it is connected.
        """
        @Interactive({}, int)
        def bar(node):
            node.send(1)

        with DeltaGraph() as graph:
            bar.call()

        with self.assertRaises(DeltaIOError):
            graph.check()


class SimpleGraph(unittest.TestCase):

    def setUp(self):
        with DeltaGraph() as graph:
            ident_ph = placeholder_node_factory()
            inter = interactive_func.call(num=ident_ph)
            ident = int_to_str(inter)
            ident_ph.specify_by_node(ident)
        self.graph = graph
        self.runtime = DeltaPySimulator(self.graph)
        self.dummy_node = ident
        self.inter_node = inter

    def test_ports(self):
        """Test if the node wires are connected correctly and have the right
        type.
        """
        interactive_node = self.graph.find_node_by_name("blah")
        dummy_node = self.graph.find_node_by_name("node")

        self.assertEqual(len(interactive_node.in_ports), 1)
        self.assertEqual(len(interactive_node.out_ports), 1)
        self.assertTupleEqual(interactive_node.out_ports[0].port_name,
                              (interactive_node.name, None))
        self.assertEqual(str(interactive_node.out_ports[0].port_type),
                         str(as_delta_type(int)))

        self.assertEqual(len(dummy_node.in_ports), 1)
        self.assertEqual(len(dummy_node.out_ports), 1)
        self.assertTupleEqual(interactive_node.out_ports[0].port_name,
                              (interactive_node.name, None))
        self.assertEqual(str(dummy_node.out_ports[0].port_type),
                         str(as_delta_type(str)))

        self.assertEqual(interactive_node.out_ports[0].destination.node,
                         dummy_node)

    def test_simulated_run(self):
        """Test if the Interactive Node performs correctly by simulating
        the runtime and the other node.
        """
        inter_node: PythonNode = self.graph.find_node_by_name("blah")
        in_q = self.runtime.in_queues[inter_node.name]["num"]
        out_q = self.runtime.out_queues[inter_node.name][None]

        thread = threading.Thread(target=inter_node.thread_worker,
                                  args=(self.runtime,))
        thread.start()

        self.assertEqual(out_q.get().msg, 3)
        in_q.put(QueueMessage("3"))
        self.assertEqual(out_q.get().msg, 4)

        thread.join()
        self.assertFalse(thread.is_alive())

    def test_real_run(self):
        """Test that the graph runs and terminates."""
        interactive_node = self.graph.find_node_by_name("blah")

        runtime = DeltaPySimulator(self.graph)
        # run for a short time - just enough for the processing to end
        runtime.run(0.1)
        # check that the interactive node has terminated
        self.assertFalse(runtime.threads[interactive_node.name].is_alive())
        runtime.stop()

    def test_graph_properties(self):
        self.graph.check()


class UpdateClockTest(unittest.TestCase):
    """Test logical clock in MessageLog.

    TODO this test case should be moved from here.
    """

    def setUp(self):
        with DeltaGraph() as self.test_graph:
            const_consumer(obj=forward.call(num=return_1()))

    def test_clock_updates(self):
        """Messages should be displayed at end of run in logical clock order.
        """
        self.rt = DeltaPySimulator(self.test_graph, msg_lvl=logging.DEBUG)
        self.rt.run()
        message_times = [msg.clk for node, _, msg in self.rt.msg_log.messages
                         if node.startswith("const_consumer")]
        self.assertGreater(len(message_times), 0)
        for time_1, time_2 in zip(message_times, message_times[1:]):
            self.assertLess(time_1, time_2)

    def test_no_message_logging(self):
        """Messages should not be logged at all.
        """
        self.rt = DeltaPySimulator(self.test_graph)
        self.rt.run()
        message_times = [msg.clk for node, _, msg in self.rt.msg_log.messages
                         if node.startswith("const_consumer")]
        self.assertEqual(message_times, [])
        for time_1, time_2 in zip(message_times, message_times[1:]):
            self.assertLess(time_1, time_2)


class ComplexGraph(unittest.TestCase):

    def setUp(self):
        """Constructs the following graph:
        +---------------------------+
        |             SAVE          |
        |   +-----+    ^            |
        +--->Add  +----+            |
            |to 10|        +----+   |
            |     +-------->    |   |
            +-----+        |ADD +---+
                     2 --->|    |
                           +----+
        """
        self.saver = StateSaver(int)

        with DeltaGraph() as graph:
            add_ph = placeholder_node_factory()
            b = return_2()
            self.int_node = add_until_10.call(num=add_ph)
            add_node = add_non_const(b, self.int_node.x)
            add_ph.specify_by_node(add_node)
            self.saver.save_and_exit(self.int_node.y)
        self.graph = graph
        self.runtime = DeltaPySimulator(self.graph)

    def test_run(self):
        """This graph should run, adding 2 to the number on every cycle."""
        self.runtime.run()
        self.assertEqual(self.saver.saved, [11])

    def test_graph_properties(self):
        self.graph.check()


if __name__ == "__main__":
    unittest.main()
