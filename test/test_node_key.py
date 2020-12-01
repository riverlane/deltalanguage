"""Various tests for ensuring when we get provide a node_key we get the node.

Done by ensuring we can receive messages from the node.

Tests for function and method blocks, as well as placeholder specify methods.
"""

import unittest

from deltalanguage.data_types import NoMessage
from deltalanguage.runtime import DeltaRuntimeExit, DeltaPySimulator
from deltalanguage.wiring import (DeltaBlock,
                              DeltaGraph,
                              DeltaMethodBlock,
                              placeholder_node_factory,
                              PythonNode)


class AddSetX:

    def __init__(self):
        self.x = None

    @DeltaMethodBlock(node_key="node")
    def add_set_x(self, a: int, b: int, node: PythonNode = None) -> NoMessage:
        self.x = node.receive('a') + node.receive('b')
        raise DeltaRuntimeExit


class TestNodeKey(unittest.TestCase):
    def test_func(self):
        @DeltaBlock(node_key="node")
        def add_assert(a: int, b: int, node: PythonNode = None) -> NoMessage:
            self.assertEqual(node.receive('a') + node.receive('b'), 9)
            raise DeltaRuntimeExit
        with DeltaGraph() as test_graph:
            add_assert(a=4, b=5)
        rt = DeltaPySimulator(test_graph)
        rt.run()

    def test_method(self):
        add_set_x = AddSetX()
        with DeltaGraph() as test_graph:
            add_set_x.add_set_x(a=4, b=5)
        rt = DeltaPySimulator(test_graph)
        rt.run()
        self.assertEqual(add_set_x.x, 9)

    def test_placeholder_func(self):
        @DeltaBlock(node_key="node")
        def add_assert(a: int, b: int, node: PythonNode = None) -> NoMessage:
            self.assertEqual(node.receive('a') + node.receive('b'), 9)
            raise DeltaRuntimeExit
        with DeltaGraph() as test_graph:
            n = placeholder_node_factory(a=4, b=5)
        n.specify_by_func(add_assert, node_key="node")
        rt = DeltaPySimulator(test_graph)
        rt.run()

    def test_placeholder_method(self):
        add_set_x = AddSetX()
        with DeltaGraph() as test_graph:
            n = placeholder_node_factory(a=4, b=5)
        n.specify_by_method(AddSetX.add_set_x, add_set_x, node_key="node")
        rt = DeltaPySimulator(test_graph)
        rt.run()
        self.assertEqual(add_set_x.x, 9)


if __name__ == "__main__":
    unittest.main()
