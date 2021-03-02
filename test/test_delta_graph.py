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
                                      Void,
                                      DeltaIOError)
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  placeholder_node_factory,
                                  RealNode)


@DeltaBlock()
def union_one_receiver(x: DUnion([int])) -> int:
    return x


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
        def test_node(a: DOptional(int)) -> Void:
            pass

        with DeltaGraph() as graph:
            p = placeholder_node_factory()
            test_node(p)

        self.assertTrue(graph.check())


def to_union_of_one(node: RealNode) -> RealNode:
    org_t = node.out_type
    node.out_type = DUnion([org_t])

    return node


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
