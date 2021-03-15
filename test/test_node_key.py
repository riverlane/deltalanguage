"""Various tests for ensuring when we get provide a node_key we get the node.

Done by ensuring we can receive messages from the node.

Tests for function and method blocks, as well as placeholder specify methods.
"""
from typing import OrderedDict
import unittest

from deltalanguage.data_types import Void
from deltalanguage.runtime import DeltaRuntimeExit, DeltaPySimulator
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  DeltaMethodBlock,
                                  NodeTemplate,
                                  placeholder_node_factory,
                                  PythonNode)


class Foo:

    def __init__(self):
        self.x = None

    @DeltaMethodBlock(node_key="node")
    def add_set_x(self, a: int, b: int, node: PythonNode = None) -> Void:
        self.x = node.receive('a') + node.receive('b')
        raise DeltaRuntimeExit


class TestNodeKey(unittest.TestCase):
    def test_func(self):
        @DeltaBlock(node_key="node")
        def add_assert(a: int, b: int, node: PythonNode = None) -> Void:
            self.assertEqual(node.receive('a') + node.receive('b'), 9)
            raise DeltaRuntimeExit
        with DeltaGraph() as test_graph:
            add_assert(a=4, b=5)
        rt = DeltaPySimulator(test_graph)
        rt.run()

    def test_method(self):
        foo = Foo()
        with DeltaGraph() as test_graph:
            foo.add_set_x(a=4, b=5)
        rt = DeltaPySimulator(test_graph)
        rt.run()
        self.assertEqual(foo.x, 9)

    def test_placeholder_func(self):
        @DeltaBlock(node_key="node")
        def add_assert(a: int, b: int, node: PythonNode = None) -> Void:
            self.assertEqual(node.receive('a') + node.receive('b'), 9)
            raise DeltaRuntimeExit
        with DeltaGraph() as test_graph:
            n = placeholder_node_factory(a=4, b=5)
        n.specify_by_func(add_assert, node_key="node")
        rt = DeltaPySimulator(test_graph)
        rt.run()

    def test_placeholder_method(self):
        foo = Foo()
        with DeltaGraph() as test_graph:
            n = placeholder_node_factory(a=4, b=5)
        n.specify_by_method(Foo.add_set_x, foo, node_key="node")
        rt = DeltaPySimulator(test_graph)
        rt.run()
        self.assertEqual(foo.x, 9)


test_template1 = NodeTemplate(name="NodeKeyTestTemplate",
                              in_params=OrderedDict([('a', int), ('b', int)]),
                              out_type=Void, node_key='node')


class Foo_T:

    def __init__(self):
        self.x = None

    @DeltaMethodBlock(node_key="node")
    def add_set_x_t(self, a: int, b: int, node: PythonNode = None) -> Void:
        self.x = node.receive('a') + node.receive('b')
        raise DeltaRuntimeExit


@DeltaBlock(template=test_template1, node_key="node")
def add_print_t(a: int, b: int, node: PythonNode = None) -> Void:
    print(node.receive('a') + node.receive('b'))
    raise DeltaRuntimeExit


class TestNodeKeyTemplated(unittest.TestCase):
    """Test that node key specification can occur correctly
    when a NodeTemplate is used.
    """

    def test_template_different_selected(self):
        """Test that node key is still correctly used on a multi-body
        node that has its body selected different from the one that was 
        specified via the constructor.
        """
        foo = Foo_T()
        with DeltaGraph() as test_graph:
            n1 = add_print_t(a=4, b=5)

        n1.add_body(foo.add_set_x_t)
        test_graph.select_bodies(preferred=["add_set_x_t"])
        DeltaPySimulator(test_graph).run()
        self.assertIn("add_set_x_t", n1.body.access_tags)
        self.assertEqual(foo.x, 9)


if __name__ == "__main__":
    unittest.main()
