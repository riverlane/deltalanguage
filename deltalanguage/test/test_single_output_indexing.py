import unittest

from deltalanguage.data_types import Int, Size
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaMethodBlock,
                                  DeltaGraph,
                                  Interactive,
                                  PythonNode)


@DeltaBlock()
def return_5_default_name() -> int:
    return 5


@DeltaBlock(outputs=[('out', int)])
def return_5() -> int:
    return 5


class MethodReturner:

    @DeltaMethodBlock()
    def return_5_default_name_m(self) -> int:
        return 5

    @DeltaMethodBlock(outputs=[('out', int)])
    def return_5_m(self) -> int:
        return 5


@Interactive(outputs=[('out', int)])
def send_5(node: PythonNode):
    node.send(5)


class TestSingleOutputIndexing(unittest.TestCase):
    """Tests for when a node has a single output, but it is still
    accessed via indexing"""

    def test_default_name_func_block(self):
        saver = StateSaver(int)

        with DeltaGraph() as graph:
            r = return_5_default_name().output
            s = saver.save_and_exit(r)

        self.assertTrue(graph.check())
        self.assertEqual(len(r.out_ports), 1)

        port_under_test = r.out_ports[0]
        self.assertEqual(port_under_test.destination.node, s)
        self.assertEqual(port_under_test.port_type, Int(Size(32)))
        self.assertEqual(port_under_test.index, 'output')

    def test_default_name_method_block(self):
        saver = StateSaver(int)
        m = MethodReturner()

        with DeltaGraph() as graph:
            r = m.return_5_default_name_m().output
            s = saver.save_and_exit(r)

        self.assertTrue(graph.check())
        self.assertEqual(len(r.out_ports), 1)

        port_under_test = r.out_ports[0]
        self.assertEqual(port_under_test.destination.node, s)
        self.assertEqual(port_under_test.port_type, Int(Size(32)))
        self.assertEqual(port_under_test.index, 'output')

    def test_custom_name_func_block(self):
        saver = StateSaver(int)

        with DeltaGraph() as graph:
            r = return_5().out
            s = saver.save_and_exit(r)

        self.assertTrue(graph.check())
        self.assertEqual(len(r.out_ports), 1)

        port_under_test = r.out_ports[0]
        self.assertEqual(port_under_test.destination.node, s)
        self.assertEqual(port_under_test.port_type, Int(Size(32)))
        self.assertEqual(port_under_test.index, 'out')

    def test_custom_name_method_block(self):
        saver = StateSaver(int)
        m = MethodReturner()

        with DeltaGraph() as graph:
            r = m.return_5_m().out
            s = saver.save_and_exit(r)

        self.assertTrue(graph.check())
        self.assertEqual(len(r.out_ports), 1)

        port_under_test = r.out_ports[0]
        self.assertEqual(port_under_test.destination.node, s)
        self.assertEqual(port_under_test.port_type, Int(Size(32)))
        self.assertEqual(port_under_test.index, 'out')

    def test_custom_name_interactive(self):
        saver = StateSaver(int)

        with DeltaGraph() as graph:
            r = send_5.call().out
            s = saver.save_and_exit(r)

        self.assertTrue(graph.check())
        self.assertEqual(len(r.out_ports), 1)

        port_under_test = r.out_ports[0]
        self.assertEqual(port_under_test.destination.node, s)
        self.assertEqual(port_under_test.port_type, Int(Size(32)))
        self.assertEqual(port_under_test.index, 'out')


@DeltaBlock(outputs=[('out1', int), ('out2', int)])
def return_5_9():
    return 5, 9


class TestMultiOutputNoIndexing(unittest.TestCase):
    """Tests for when a node has more than one output, but it is still 
    accessed not using indexing"""

    def test_default_name_func_block(self):
        saver = StateSaver(int)

        with self.assertRaises(ValueError):
            with DeltaGraph():
                saver.save_and_exit(return_5_9())


if __name__ == "__main__":
    unittest.main()
