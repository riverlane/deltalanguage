"""Test the functioning of the Delta runtime."""

import logging
import time
import unittest

from test._utils import (OtherClass,
                         SomeClass,
                         add,
                         add1_or0,
                         async_err_if_4,
                         do_nothing,
                         opt_increment,
                         return_2,
                         return_4)

from deltalanguage.data_types import DOptional
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import (ConstQueue,
                                   DeltaQueue,
                                   DeltaPySimulator,
                                   DeltaRuntimeExit)
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  Interactive,
                                  PyFuncNode,
                                  PyMethodNode,
                                  PyInteractiveNode,
                                  placeholder_node_factory)


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        r"""Build the following graph
        ```
                    add_1
                    /   \
                   ||   ||
                   ||   ||
                    \   /
                   increment ----------> saver
        ```
        """
        self.saver = StateSaver(int)
        with DeltaGraph() as my_graph:
            add_1_placeholder = placeholder_node_factory()
            incr_node = opt_increment.call(n=add_1_placeholder)
            self.saver.save_and_exit(incr_node.y)
            add_one = add1_or0(incr_node.x)
            add_1_placeholder.specify_by_node(add_one)

        self.graph = my_graph
        self.rt = DeltaPySimulator(my_graph)

    def test_creation(self):
        self.assertIsInstance(self.rt, DeltaPySimulator)

    def test_queues(self):
        """Test if everything in the queue dicts is the right type."""
        self.assertIsInstance(self.rt.in_queues, dict)
        self.assertIsInstance(self.rt.out_queues, dict)

        for key, val in self.rt.out_queues.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(val, dict)
            for port_index, qu in val.items():
                self.assertTrue(isinstance(port_index, str) or
                                port_index is None)
                self.assertIsInstance(qu, DeltaQueue)

        for key, val in self.rt.in_queues.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(val, dict)
            for port_index, qu in val.items():
                self.assertTrue(isinstance(port_index, str) or
                                port_index is None)
                self.assertIsInstance(qu, DeltaQueue)

    def test_run(self):
        """Do the running of the runtime."""
        self.rt.run()
        self.assertEqual(self.saver.saved, [3])

    def test_graph_properties(self):
        self.graph.check()


class DeltaMethodBlockTest(unittest.TestCase):
    """Test the functionality of creating Method Nodes."""

    def setUp(self):
        self.inst = SomeClass()
        self.saver = StateSaver(int)
        with DeltaGraph() as my_graph:
            method_node = self.inst.method()
            self.saver.save_and_exit(method_node)

        self.graph = my_graph
        self.method_node = my_graph.nodes[0]

    def test_creation(self):
        self.assertIsInstance(self.method_node, PyMethodNode)

    def test_name(self):
        self.assertIn("methodnode", self.method_node.name)

    def test_instace(self):
        self.assertIs(self.method_node.body.instance, self.inst)

    def test_run(self):
        rt = DeltaPySimulator(self.graph)
        rt.run()
        self.assertEqual(self.saver.saved, [1])

    def test_graph_properties(self):
        self.graph.check()


class MixedGraphTest(unittest.TestCase):

    def setUp(self):
        """
        Create the graph:
        return_4 -> add -> add_member -> print -> saver
                  /
        return_2 /
        """
        self.saver = StateSaver(int)

        with DeltaGraph() as my_graph:
            inst = OtherClass(2)
            const = add(return_4(), return_2())
            num = inst.add_member(const)
            self.saver.save_and_exit(num)

        self.graph = my_graph
        self.runtime = DeltaPySimulator(my_graph)

    def test_creation(self):
        self.assertIsInstance(self.runtime, DeltaPySimulator)

    def test_queue_type(self):
        """Check that queues of the correct type are being created.
        """
        with self.subTest(msg="Queue out of add_member should be aged"):
            method_node = self.graph.find_node_by_name("add_member")
            self.assertIsInstance(
                self.runtime.out_queues[method_node.name][None], DeltaQueue)

        with self.subTest(msg="Queue out of const node should be const queue"):
            const_node = self.graph.find_node_by_name("add")
            self.assertIsInstance(
                self.runtime.out_queues[const_node.name][None], ConstQueue)

    def test_optional(self):
        """Test that the queue out of add_member and into the printer is
        mandatory.
        """
        method_node = self.graph.find_node_by_name("add_member")
        is_opt = self.runtime.out_queues[method_node.name][None].optional
        self.assertFalse(is_opt)

    def test_start(self):
        self.runtime.start()
        time.sleep(0.1)
        self.runtime.stop()

    def test_run(self):
        """Test that running the graph produces the right output """
        self.runtime.run()
        self.assertEqual(self.saver.saved, [8])

    def test_graph_properties(self):
        self.graph.check()


class ExceptionHandlingTest(unittest.TestCase):

    def test_error_async_nodes(self):
        """Test that an error in a node is re-thrown."""
        with DeltaGraph() as graph:
            n = SomeClass().method()
            async_err_if_4(n)
        rt = DeltaPySimulator(graph, lvl=logging.FATAL)
        with self.assertRaises(RuntimeError):
            rt.run()
        self.assertFalse(rt.running)

    def test_exit_(self):
        """Test that an DeltaRuntimeExit does not cause an error."""
        s = StateSaver(int, condition=lambda x: x == 4)

        with DeltaGraph() as graph:
            n = SomeClass().method()
            s.save_and_exit_if(n)

        rt = DeltaPySimulator(graph)
        rt.run()

        self.assertFalse(rt.running)
        self.assertEqual(s.saved, [1, 2, 3, 4])


class RuntimeConstantNodeTest(unittest.TestCase):
    """Testing simple graphs with constant nodes."""

    def setUp(self):
        self.result = 0

        @DeltaBlock()
        def const_save_exit(n: int) -> int:
            self.result = n
            raise DeltaRuntimeExit
        self.const_save_exit = const_save_exit

    def test_exit_const_node(self):
        """Test that a DeltaRuntimeExit in a constant node does not cause an
        error.
        """
        with DeltaGraph() as graph:
            do_nothing(n=self.const_save_exit(n=add(n1=1, n2=2)))
        with self.assertRaises(RuntimeError):
            rt = DeltaPySimulator(graph)
            rt.run()

    def test_exit_all_const_nodes(self):
        """Test that runtime runs correctly if all nodes are constant."""
        with DeltaGraph() as graph:
            self.const_save_exit(n=add(n1=1, n2=2))
        with self.assertRaises(RuntimeError):
            rt = DeltaPySimulator(graph)
            rt.run(100)


class RuntimeConstantNodeAndPlaceholderTest(unittest.TestCase):
    """Testing that a loop of constant nodes cannot be created via
    PlaceholderNode.
    """

    def setUp(self):
        @DeltaBlock(allow_const=True)
        def printer_1(n: int) -> int:
            return n

        def printer_2(n: int) -> int:
            return n

        self.printer_1 = printer_1
        self.printer_2 = printer_2

    def test_specify_by_node(self):
        with DeltaGraph() as graph:
            p = placeholder_node_factory()
            b = self.printer_1(p)
            p.specify_by_node(self.printer_1(b))

        for node in graph.nodes:
            self.assertIsInstance(node, PyFuncNode)

    def test_specify_by_func(self):
        with DeltaGraph() as graph:
            p_1 = placeholder_node_factory()
            p_2 = placeholder_node_factory(p_1)
            p_1.specify_by_node(self.printer_1(p_2))
            p_2.specify_by_func(self.printer_2, allow_const=True)

        for node in graph.nodes:
            self.assertIsInstance(node, PyFuncNode)

    def test_const_selfloop(self):
        with DeltaGraph() as graph:
            p = placeholder_node_factory()
            p.specify_by_node(self.printer_1(p))

        for node in graph.nodes:
            self.assertIsInstance(node, PyFuncNode)


class RuntimeConstantNodeAndDOptionalTest(unittest.TestCase):
    """Testing that a constant node _always_ provide messages, even if the
    receiving port has DOptional.

    TODO: there is something non-deterministic in the behaiviour of this test.
    Most of the times it runs quickly (<< 1 second), but occasionally it's
    much slower.
    """

    def test_one(self):
        n_iter = 1000
        saver = StateSaver(int)

        @Interactive({}, int)
        def generator(node: PyInteractiveNode):
            for _ in range(n_iter):
                node.send(1)

        @DeltaBlock()
        def adder(a: DOptional(int), b: int) -> int:
            if a is None:
                return b
            else:
                return a + b

        @Interactive({'a': int}, int)
        def aggregator(node: PyInteractiveNode):
            result = 0
            for _ in range(n_iter):
                a = node.receive('a')
                result += a
            node.send(result)

        with DeltaGraph() as graph:
            total = adder(10, generator.call())
            saver.save_and_exit(aggregator.call(a=total))

        rt = DeltaPySimulator(graph)
        rt.run()

        self.assertEqual(saver.saved, [11 * n_iter])


if __name__ == "__main__":
    unittest.main()
