import logging
import threading
import unittest


from deltalanguage.data_types import as_delta_type, DeltaIOError, Optional
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage._utils import QueueMessage
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaMethodBlock,
                                  DeltaGraph,
                                  Interactive,
                                  PythonNode,
                                  placeholder_node_factory,
                                  InteractiveBodyTemplate)
from deltalanguage.test._utils import (add_non_const,
                                       const_consumer,
                                       return_1,
                                       return_2,
                                       TripleStateSaver)


@DeltaBlock(name="node")
def int_to_str(n: int) -> str:
    return str(n)


@Interactive(inputs=[("num", str)], outputs=[('out', int)], name="blah")
def interactive_func(node: PythonNode):
    node.send(3)
    num = node.receive()["num"]
    num = int(num, base=10)
    node.send(num + 1)


@Interactive(inputs=[("num", int)], outputs=[('out', int)])
def forward(node: PythonNode):
    for _ in range(10):
        num = node.receive("num")
        node.send(num)
    raise DeltaRuntimeExit


@Interactive(inputs=[("num", int)], outputs=[('x', int), ('y', int)])
def add_until_10(node: PythonNode):
    """Sends num on the left port until it is greater than 10, then sends it
    on the right port.
    """
    num = 1
    while num < 10:
        node.send(num, None)
        num = node.receive()["num"]
    node.send(None, num)


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
            @Interactive()
            def _bar(node):
                while True:
                    pass

    def test_interactive_node_without_ports(self):
        """An interactive node with I/O can be just forgotten during graph
        construction. We check that it is connected.
        """
        @Interactive(outputs=[('output', int)])
        def bar(node):
            node.send(1)

        with DeltaGraph() as graph:
            bar.call()

        with self.assertRaises(DeltaIOError):
            graph.check()

    def test_interactive_inputs_by_position(self):
        """Test that interactive inputs can now be given positionally in wiring
        """
        @Interactive([('a', int), ('b', float)], [('output', int)])
        def add_int_float(node):
            a = node.receive('a')
            b = node.receive('b')
            node.send(a + b)

        with DeltaGraph() as graph:
            add_int_float.call(1, 2.2)

        self.assertTrue(graph.check())

    def test_interactive_inputs_by_hybrid(self):
        """Test that interactive inputs can now be given positionally and
        by keyword at the same time in wiring
        """
        @Interactive([('a', int), ('b', float)], [('output', int)])
        def add_int_float(node):
            a = node.receive('a')
            b = node.receive('b')
            node.send(a + b)

        with DeltaGraph() as graph:
            add_int_float.call(90, b=7.7)

        self.assertTrue(graph.check())


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
                              (interactive_node.name, 'out'))
        self.assertEqual(str(interactive_node.out_ports[0].port_type),
                         str(as_delta_type(int)))

        self.assertEqual(len(dummy_node.in_ports), 1)
        self.assertEqual(len(dummy_node.out_ports), 1)
        self.assertTupleEqual(interactive_node.out_ports[0].port_name,
                              (interactive_node.name, 'out'))
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
        out_q = self.runtime.out_queues[inter_node.name]["out"]

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


@Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def positional_send(node: PythonNode):
    """Send to multiple outputs via different positional methods
    None, or not specifying enough positions can be used to send nothing
    """
    node.send(1, 2, False)
    node.send(3, 4)
    node.send(5)
    node.send(6, None)
    node.send(None, None, True)
    node.send(7, None, False)
    node.send(10)


@Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def keyword_send(node: PythonNode):
    """Send to multiple outputs via different keyword methods
    None, or just not specficing a keyword can be used to send nothing
    """
    node.send(x=1)
    node.send(y=2)
    node.send()
    node.send(z=True)
    node.send(x=3, y=4, z=False)
    node.send(x=5, y=6)
    node.send(x=7, z=False)
    node.send(y=8, z=True)
    node.send(y=None, x=9, z=None)
    node.send(z=False, x=None)
    node.send(x=10)


@Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def positional_and_keyword_send(node: PythonNode):
    """Send to multiple outputs via hybrid positional and keyword methods
    None, or just not specficing a keyword/position can be used to send nothing
    """
    node.send(1, 2, z=False)
    node.send(3, y=4)
    node.send(5, z=True)
    node.send(None, z=False, y=6)
    node.send(None, 7, z=True)
    node.send(8, None, z=False)
    node.send(10, y=None, z=None)


@Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def multiple_specify_kwarg_position_first(node: PythonNode):
    """Specify the same value twice, once by posiiton and once by keyword
    """
    node.send(1, x=5)


@Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def multiple_specify_kwarg_position_second(node: PythonNode):
    """Specify the same value twice, once by posiiton and once by keyword
    on not the first value in outputs order
    """
    node.send(1, 2, y=5)


@Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def too_many_positional(node: PythonNode):
    """Attempt to send too many positional arguments out of a node
    """
    node.send(1, 2, False, 3)


@Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def invalid_kwarg(node: PythonNode):
    """Attempt to send via an invalid keyword
    """
    node.send(x=1, foo=7)


class TestInteractiveSendBehaviour(unittest.TestCase):
    """Test the different ways an interactive body can use
    `node.send()` to send values to multiple outputs
    """

    def test_positional_interactive_send(self):
        ts = TripleStateSaver(11)

        with DeltaGraph() as graph:
            i_send = positional_send.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        DeltaPySimulator(graph).run()

        self.assertEqual(ts.x_store, [1, 3, 5, 6, 7, 10])
        self.assertEqual(ts.y_store, [2, 4])
        self.assertEqual(ts.z_store, [False, True, False])

    def test_keyword_interactive_send(self):
        ts = TripleStateSaver(15)

        with DeltaGraph() as graph:
            i_send = keyword_send.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        DeltaPySimulator(graph).run()

        self.assertEqual(ts.x_store, [1, 3, 5, 7, 9, 10])
        self.assertEqual(ts.y_store, [2, 4, 6, 8])
        self.assertEqual(ts.z_store, [True, False, False, True, False])

    def test_keyword_positional_interactive_send(self):
        ts = TripleStateSaver(14)

        with DeltaGraph() as graph:
            i_send = positional_and_keyword_send.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        DeltaPySimulator(graph).run()

        self.assertEqual(ts.x_store, [1, 3, 5, 8, 10])
        self.assertEqual(ts.y_store, [2, 4, 6, 7])
        self.assertEqual(ts.z_store, [False, True, False, True, False])

    def test_invalid_kwarg(self):
        ts = TripleStateSaver(1)

        with DeltaGraph() as graph:
            i_send = invalid_kwarg.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        with self.assertRaises(RuntimeError):
            DeltaPySimulator(graph).run()

    def test_too_many_positional(self):
        ts = TripleStateSaver(1)

        with DeltaGraph() as graph:
            i_send = too_many_positional.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        with self.assertRaises(RuntimeError):
            DeltaPySimulator(graph).run()

    def test_multi_specify_by_position_and_kwarg(self):
        saver_x = StateSaver(int)

        with DeltaGraph() as graph_1:
            i_send = multiple_specify_kwarg_position_first.call()
            saver_x.save_and_exit_if(i_send.x)

        with self.assertRaises(RuntimeError):
            DeltaPySimulator(graph_1).run()

        saver_x = StateSaver(int, lambda x: x >= 10)
        saver_y = StateSaver(int)

        with DeltaGraph() as graph_2:
            i_send = multiple_specify_kwarg_position_second.call()
            saver_x.save_and_exit_if(i_send.x)
            saver_y.save(i_send.y)

        with self.assertRaises(RuntimeError):
            DeltaPySimulator(graph_2).run()


if __name__ == "__main__":
    unittest.main()
