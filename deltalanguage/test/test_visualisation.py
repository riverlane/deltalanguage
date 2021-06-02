"""Tests for graph visualisation.
Mainly testing that NetworkX returns the correct form of graph.
Done by comparing nodes and edges. Note that node numbers have
to be stripped, due to the numbers varying depending on how
many graphs are created.
"""

from collections import Counter
import unittest

from deltalanguage.data_types import Void, Optional
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock, DeltaGraph,
                                  placeholder_node_factory)

from deltalanguage.test._node_lib import add_non_const


@DeltaBlock()
def print_until_10(n: int) -> int:
    print(n)
    if n >= 10:
        raise DeltaRuntimeExit
    else:
        return n


def node_cnt(nodes):
    """Constructs Counter of nodes and strips number from node names."""
    return Counter(["_".join(node.split("_")[:-1]) for node in list(nodes)])


def edge_cnt(edges):
    """Constructs Counter of edges and strips number from node names."""
    return Counter(
        [("_".join(edge[0].split("_")[:-1]), "_".join(edge[1].split("_")[:-1]))
         for edge in list(edges)]
    )


class SimpleGraphTest(unittest.TestCase):
    """Testing for a simple graph with four nodes."""

    def test_simple_networkx_graph(self):
        s = StateSaver(int)

        with DeltaGraph() as graph:
            n = add_non_const(3, 4)
            s.save_and_exit(n)

        networkx_graph = graph.get_networkx_graph()

        self.assertEqual(node_cnt(networkx_graph.nodes()),
                         Counter({'node': 2, 'add_non_const': 1,
                                  'save_and_exit': 1}))
        self.assertEqual(edge_cnt(networkx_graph.edges()),
                         Counter({('node', 'add_non_const'): 2,
                                  ('add_non_const', 'save_and_exit'): 1}))


class ComplexGraphTest(unittest.TestCase):
    """Testing for a graph with a cycle."""

    def test_complex_networkx_graph(self):
        with DeltaGraph() as complex_graph:
            ph = placeholder_node_factory()
            n = add_non_const(1, ph)
            print_node = print_until_10(n=n)
            ph.specify_by_node(print_node)
        networkx_graph = complex_graph.get_networkx_graph()
        self.assertEqual(node_cnt(networkx_graph.nodes()),
                         Counter({'node': 1, 'add_non_const': 1,
                                  'print_until_10': 1}))
        self.assertEqual(edge_cnt(networkx_graph.edges()),
                         Counter({('node', 'add_non_const'): 1,
                                  ('add_non_const', 'print_until_10'): 1,
                                  ('print_until_10', 'add_non_const'): 1}))


if __name__ == "__main__":
    unittest.main()
