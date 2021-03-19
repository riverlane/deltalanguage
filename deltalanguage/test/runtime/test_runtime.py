"""Test the functioning of the Delta runtime."""

import logging
import time
import unittest

import deltalanguage as dl

from deltalanguage.test._utils import (OtherClass,
                                       SomeClass,
                                       add,
                                       add1_or0,
                                       async_err_if_4,
                                       do_nothing,
                                       opt_increment,
                                       return_2,
                                       return_4)


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
        self.saver = dl.lib.StateSaver(int)
        with dl.DeltaGraph() as graph:
            add_1_placeholder = dl.placeholder_node_factory()
            incr_node = opt_increment.call(n=add_1_placeholder)
            self.saver.save_and_exit(incr_node.y)
            add_one = add1_or0(incr_node.x)
            add_1_placeholder.specify_by_node(add_one)

        self.graph = graph
        self.rt = dl.DeltaPySimulator(graph)

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
                self.assertIsInstance(qu, dl.runtime.DeltaQueue)

        for key, val in self.rt.in_queues.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(val, dict)
            for port_index, qu in val.items():
                self.assertTrue(isinstance(port_index, str) or
                                port_index is None)
                self.assertIsInstance(qu, dl.runtime.DeltaQueue)

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
        self.saver = dl.lib.StateSaver(int)
        with dl.DeltaGraph() as graph:
            method_node = self.inst.method()
            self.saver.save_and_exit(method_node)

        self.graph = graph
        self.method_node = graph.nodes[0]

    def test_creation(self):
        self.assertIsInstance(self.method_node.body, dl.wiring.PyMethodBody)

    def test_name(self):
        self.assertIn("methodnode", self.method_node.name)

    def test_instace(self):
        self.assertIs(self.method_node.body.instance, self.inst)

    def test_run(self):
        dl.DeltaPySimulator(self.graph).run()
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
        self.saver = dl.lib.StateSaver(int)

        with dl.DeltaGraph() as graph:
            inst = OtherClass(2)
            const = add(return_4(), return_2())
            num = inst.add_member(const)
            self.saver.save_and_exit(num)

        self.graph = graph
        self.runtime = dl.DeltaPySimulator(graph)

    def test_queue_type(self):
        """Check that queues of the correct type are being created.
        """
        with self.subTest(msg="Queue out of add_member should be aged"):
            method_node = self.graph.find_node_by_name("add_member")
            self.assertIsInstance(
                self.runtime.out_queues[method_node.name][None],
                dl.runtime.DeltaQueue)

        with self.subTest(msg="Queue out of const node should be const queue"):
            const_node = self.graph.find_node_by_name("add")
            self.assertIsInstance(
                self.runtime.out_queues[const_node.name][None],
                dl.runtime.ConstQueue)

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
        with dl.DeltaGraph() as graph:
            n = SomeClass().method()
            async_err_if_4(n)

        rt = dl.DeltaPySimulator(graph, lvl=logging.FATAL)

        with self.assertRaises(RuntimeError):
            rt.run()
        self.assertFalse(rt.running)

    def test_exit_(self):
        """Test that an DeltaRuntimeExit does not cause an error."""
        s = dl.lib.StateSaver(int, condition=lambda x: x == 4)

        with dl.DeltaGraph() as graph:
            n = SomeClass().method()
            s.save_and_exit_if(n)

        rt = dl.DeltaPySimulator(graph)
        rt.run()

        self.assertFalse(rt.running)
        self.assertEqual(s.saved, [1, 2, 3, 4])


class RuntimeConstantNodeTest(unittest.TestCase):
    """Testing simple graphs with constant nodes."""

    def setUp(self):
        self.result = 0

        @dl.DeltaBlock()
        def const_save_exit(n: int) -> int:
            self.result = n
            raise dl.DeltaRuntimeExit

        self.const_save_exit = const_save_exit

    def test_exit_const_node(self):
        """Test that a DeltaRuntimeExit in a constant node does not cause an
        error.
        """
        with dl.DeltaGraph() as graph:
            do_nothing(n=self.const_save_exit(n=add(n1=1, n2=2)))

        with self.assertRaises(RuntimeError):
            dl.DeltaPySimulator(graph).run()

    def test_exit_all_const_nodes(self):
        """Test that runtime runs correctly if all nodes are constant."""
        with dl.DeltaGraph() as graph:
            self.const_save_exit(n=add(n1=1, n2=2))

        with self.assertRaises(RuntimeError):
            dl.DeltaPySimulator(graph).run(100)


class RuntimeConstantNodeAndPlaceholderTest(unittest.TestCase):
    """Testing that a loop of constant nodes cannot be created via
    PlaceholderNode.
    """

    def setUp(self):
        @dl.DeltaBlock(allow_const=True)
        def printer_1(n: int) -> int:
            return n

        def printer_2(n: int) -> int:
            return n

        self.printer_1 = printer_1
        self.printer_2 = printer_2

    def test_specify_by_node(self):
        with dl.DeltaGraph() as graph:
            p = dl.placeholder_node_factory()
            b = self.printer_1(p)
            p.specify_by_node(self.printer_1(b))

        for node in graph.nodes:
            self.assertIsInstance(node.body, dl.wiring.PyFuncBody)

    def test_specify_by_func(self):
        with dl.DeltaGraph() as graph:
            p_1 = dl.placeholder_node_factory()
            p_2 = dl.placeholder_node_factory(p_1)
            p_1.specify_by_node(self.printer_1(p_2))
            p_2.specify_by_func(self.printer_2, allow_const=True)

        for node in graph.nodes:
            self.assertIsInstance(node.body, dl.wiring.PyFuncBody)

    def test_const_selfloop(self):
        with dl.DeltaGraph() as graph:
            p = dl.placeholder_node_factory()
            p.specify_by_node(self.printer_1(p))

        for node in graph.nodes:
            self.assertIsInstance(node.body, dl.wiring.PyFuncBody)


class RuntimeConstantNodeAndDOptionalTest(unittest.TestCase):
    """Testing that a constant node _always_ provides messages, even if the
    receiving port is optional (case 1).
    It's ensured by evaluating constant nodes before runtime simulation.

    Non-constant nodes providing inputs to an optional input can be
    delayed, thus a message can arrive too late (case 2).
    """

    def test_main(self):
        n_iter = 1000
        s = dl.lib.StateSaver(int)
        gen = dl.lib.make_generator(1, reps=n_iter)

        @dl.DeltaBlock(allow_const=True)
        def return10_const() -> int:
            return 10

        @dl.DeltaBlock(allow_const=False)
        def return10_non_const() -> int:
            return 10

        @dl.DeltaBlock()
        def adder(a: dl.DOptional(int), b: int) -> int:
            if a is None:
                return b
            else:
                return a + b

        @dl.Interactive([('a', int)], int)
        def aggregator(node):
            result = 0
            for _ in range(n_iter):
                a = node.receive('a')
                result += a
            node.send(result)

        # Case 1: const nodes always provide an input for optional ports

        with dl.DeltaGraph() as graph:
            total = adder(return10_const(), gen.call())
            s.save_and_exit(aggregator.call(a=total))

        dl.DeltaPySimulator(graph).run()

        self.assertEqual(s.saved[-1], 11 * n_iter)

        # Case 2: due to uncontrolled delays non-const nodes not always
        # provide an input for optional ports

        s.reset()
        gen = dl.lib.make_generator(1, reps=n_iter)

        with dl.DeltaGraph() as graph:
            total = adder(return10_non_const(), gen.call())
            s.save_and_exit(aggregator.call(a=total))

        dl.DeltaPySimulator(graph).run()

        self.assertLessEqual(s.saved[-1], 11 * n_iter)


if __name__ == "__main__":
    unittest.main()
