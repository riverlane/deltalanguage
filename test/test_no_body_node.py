import unittest
from collections import OrderedDict

from deltalanguage._utils import NamespacedName
from deltalanguage.data_types import (DBool, DInt, DOptional, DeltaTypeError,
                                      Void, make_forked_return)
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaMethodBlock,
                                  DeltaGraph,
                                  ForkedNode,
                                  Interactive,
                                  placeholder_node_factory,
                                  NodeTemplate,
                                  MigenNodeTemplate,
                                  PyMigenBody,
                                  RealNode)


class NoBodyNodeTest(unittest.TestCase):
    """Tests regarding using `NodeTemplate` to create a node with no bodies
    """

    def setUp(self):
        def func_for_placeholder() -> int:
            return 7
        self.func_for_placeholder = func_for_placeholder

    def test_forked_input(self):
        ForkedReturnT, ForkedReturn = make_forked_return({'a': int, 'b': bool})
        template_2 = NodeTemplate(in_params={'a': int, 'b': bool})

        @DeltaBlock()
        def add_1_true(n: int) -> ForkedReturnT:
            return ForkedReturn(a=n+1, b=True)

        with DeltaGraph() as graph:
            forked_input = add_1_true(n=5)
            template_2.call(a=forked_input.a, b=forked_input.b)

        self.assertTrue(graph.check())

    def test_placeholder_input(self):
        template_3 = NodeTemplate(in_params=OrderedDict([('a', int)]))

        with DeltaGraph() as graph:
            a = placeholder_node_factory()
            template_3.call(a=a)

        a.specify_by_func(self.func_for_placeholder)
        self.assertTrue(graph.check())

    def test_partial_arg_types(self):
        template_4 = NodeTemplate(in_params={'a': int, 'b': bool})

        @DeltaBlock()
        def bool_and(a: bool, b: bool) -> bool:
            return a and b
        with DeltaGraph() as graph:
            a = placeholder_node_factory()
            template_4.call(a=a,
                            b=bool_and(a=True, b=False))

        a.specify_by_func(self.func_for_placeholder)
        self.assertTrue(graph.check())

    def test_template_input_raises_exception(self):
        @DeltaBlock()
        def add(a: int, b: int) -> int:
            return a+b

        template_1 = NodeTemplate(in_params={'a': bool})

        with self.assertRaises(DeltaTypeError):
            with DeltaGraph() as graph:
                template_1.call(a=add(a=1, b=2))
            graph.check()


class OpCacher2():

    def __init__(self):
        self._add_cache = {}

    @DeltaMethodBlock()
    def cached_add(self, a: int, b: int) -> int:
        if (a, b) in self._add_cache:
            return self._add_cache[(a, b)]
        else:
            result = a+b
            self._add_cache[(a, b)] = result
            return result


class NoBodyAddBody(unittest.TestCase):
    """Tests for when the default call is used to create a node with no bodies
    and then ``add_body`` is used to give the node a body. 
    """

    def test_add_func(self):
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(allow_const=False)
        def simple_add(a: int, b: int) -> int:
            return a + b

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 0)
        n1.add_body(simple_add)
        self.assertEqual(len(n1.bodies), 1)
        self.assertIn('simple_add', n1.body.access_tags)

    def test_add_method(self):
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)
        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 0)
        n1.add_body(OpCacher2().cached_add)
        self.assertEqual(len(n1.bodies), 1)
        self.assertIn('cached_add', n1.body.access_tags)

    def test_add_multiple(self):
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(allow_const=False)
        def simple_add(a: int, b: int) -> int:
            return a + b

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 0)
        n1.add_body(OpCacher2().cached_add)
        n1.add_body(simple_add)
        self.assertEqual(len(n1.bodies), 2)
        self.assertIn('cached_add', n1.body.access_tags)

    def test_add_interactive(self):
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @Interactive(in_params=OrderedDict([('a', int), ('b', int)]),
                     out_type=int)
        def broken_adder(node: RealNode):
            a = node.receive('a')
            b = node.receive('b')
            node.send(a+b+1)

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 0)
        n1.add_body(broken_adder)
        self.assertEqual(len(n1.bodies), 1)
        self.assertIn('broken_adder', n1.body.access_tags)

    def test_add_migen(self):
        test_template1 = NodeTemplate(
            name="test_1",
            in_params={'a': DOptional(int), 'b': DOptional(int)}
        )

        class AMigenNode(MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', DOptional(int))
                template.add_pa_in_port('b', DOptional(int))

        with DeltaGraph():
            n1 = test_template1.call(a=2, b=3)

        self.assertEqual(len(n1.bodies), 0)
        n1.add_body(AMigenNode())
        self.assertEqual(len(n1.bodies), 1)
        self.assertIn(PyMigenBody, n1.body.access_tags)

    def test_add_invalid_body(self):
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(allow_const=False)
        def simple_add_to_bool(a: int, b: int) -> bool:
            return bool(a + b)

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        with self.assertRaises(ValueError):
            n1.add_body(simple_add_to_bool)


if __name__ == "__main__":
    unittest.main()
