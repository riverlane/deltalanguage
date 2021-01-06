"""Test properties of DeltaGraph:

- test check method with good and bad graphs
- test DeltaGraph flattening
"""

import unittest

from test._utils import return_1

from deltalanguage.data_types import (DArray,
                                      DOptional,
                                      DSize,
                                      DTuple,
                                      DUnion,
                                      NoMessage,
                                      DeltaIOError)
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  placeholder_node_factory,
                                  to_list_of_one,
                                  to_tuple_of_one,
                                  to_union_of_one)


@DeltaBlock()
def union_one_receiver(x: DUnion([int])) -> int:
    return x


@DeltaBlock()
def list_one_receiver(x: DArray(int, DSize(1))) -> int:
    return x[0]


@DeltaBlock()
def tuple_one_receiver(x: DTuple([int])) -> int:
    return x[0]


class ExplcitCastsTest(unittest.TestCase):
    """Tests to ensure the four explicit type casts work properly."""

    def setUp(self):
        self.s = StateSaver(object)

    def test_union(self):
        with DeltaGraph() as graph:
            self.s.save_and_exit(union_one_receiver(
                to_union_of_one(return_1())))

        rt = DeltaPySimulator(graph)
        rt.run()
        self.assertEqual(self.s.saved, [1])

    def test_list(self):
        with DeltaGraph() as graph:
            self.s.save_and_exit(list_one_receiver(to_list_of_one(return_1())))

        rt = DeltaPySimulator(graph)
        rt.run()
        self.assertEqual(self.s.saved, [1])

    def test_tuple(self):
        with DeltaGraph() as graph:
            self.s.save_and_exit(tuple_one_receiver(
                to_tuple_of_one(return_1())))

        rt = DeltaPySimulator(graph)
        rt.run()
        self.assertEqual(self.s.saved, [1])


class DeltaGraphTest(unittest.TestCase):
    """Verification of the graph."""

    def test_loose_output(self):
        """Loose output wire don't cause a problem"""
        s = StateSaver(int)
        with DeltaGraph() as graph:
            s.transfer(4)

        node = graph.find_node_by_name('transfer')
        self.assertTrue(len(node.out_ports) == 0)
        self.assertTrue(graph.check())

    def test_loose_input(self):
        """Loose input wire is bad."""
        s = StateSaver(int)
        with DeltaGraph() as graph:
            p = placeholder_node_factory()
            s.transfer(p)

        with self.assertRaises(DeltaIOError):
            graph.check()

    def test_loose_optional_input(self):
        """Optional input without input does not raise an error."""
        @DeltaBlock(allow_const=False)
        def test_node(a: DOptional(int)) -> NoMessage:
            pass

        with DeltaGraph() as graph:
            p = placeholder_node_factory()
            test_node(p)

        self.assertTrue(graph.check())


class DeltaGraphStrTest(unittest.TestCase):
    """Test for correct graph printing."""

    def test_graph_str_output(self):
        """Stringify a pre-defined graph and compare output to test data"""

        DeltaGraph.clean_stack()
        s = StateSaver(object)

        with DeltaGraph() as graph:
            s.save_and_exit(union_one_receiver(
                to_union_of_one(return_1())))

        with open('test/data/graph_str.txt', 'r') as file:
            correct_str = file.read()

        self.assertEqual(str(graph), correct_str)


if __name__ == "__main__":
    unittest.main()
