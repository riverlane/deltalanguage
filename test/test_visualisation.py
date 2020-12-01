"""Tests for graph visualisation.
Mainly testing that NetworkX returns the correct form of graph.
Done by comparing nodes and edges. Note that node numbers have
to be stripped, due to the numbers varying depending on how
many graphs are created.
"""

from collections import Counter
import unittest

from deltalanguage.data_types import NoMessage, DOptional
from deltalanguage.runtime import DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock, DeltaGraph,
                                  placeholder_node_factory)


@DeltaBlock()
def add(a: int, b: DOptional(int)) -> int:
    if b is None:
        return a
    else:
        return a+b


@DeltaBlock()
def print_then_exit(n: int) -> NoMessage:
    print(n)
    raise DeltaRuntimeExit


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
    return Counter([("_".join(edge[0].split("_")[:-1]),
                     "_".join(edge[1].split("_")[:-1])) for edge in list(edges)])


class SimpleGraph(unittest.TestCase):
    """Testing for a simple graph with four nodes."""

    def test_simple_networkx_graph(self):
        with DeltaGraph() as simple_graph:
            n = add(a=3, b=4)
            print_then_exit(n=n)
        networkx_graph = simple_graph.get_networkx_graph()
        self.assertEqual(node_cnt(networkx_graph.nodes()),
                         Counter({'node': 2, 'add': 1, 'print_then_exit': 1}))
        self.assertEqual(edge_cnt(networkx_graph.edges()),
                         Counter({('node', 'add'): 2,
                                  ('add', 'print_then_exit'): 1}))


class ComplexGraph(unittest.TestCase):
    """Testing for a graph with a cycle."""

    def test_complex_networkx_graph(self):
        with DeltaGraph() as complex_graph:
            ph = placeholder_node_factory()
            n = add(a=1, b=ph)
            print_node = print_until_10(n=n)
            ph.specify_by_node(print_node)
        networkx_graph = complex_graph.get_networkx_graph()
        self.assertEqual(node_cnt(networkx_graph.nodes()),
                         Counter({'node': 1, 'add': 1, 'print_until_10': 1}))
        self.assertEqual(edge_cnt(networkx_graph.edges()),
                         Counter({('node', 'add'): 1,
                                  ('add', 'print_until_10'): 1,
                                  ('print_until_10', 'add'): 1}))


if __name__ == "__main__":
    unittest.main()
