import unittest

from deltalanguage.data_types import Optional, DeltaTypeError
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaMethodBlock,
                                  DeltaGraph,
                                  Interactive,
                                  placeholder_node_factory,
                                  NodeTemplate,
                                  MigenNodeTemplate,
                                  PyMigenBody,
                                  RealNode)

from deltalanguage.test._node_lib import add_const, add_non_const


class NoBodyNodeTest(unittest.TestCase):
    """Tests regarding using `NodeTemplate` to create a node with no bodies
    """

    def setUp(self):
        def func_for_placeholder() -> int:
            return 7
        self.func_for_placeholder = func_for_placeholder

    def test_multi_input_from_same(self):
        template_2 = NodeTemplate(inputs=[('a', int), ('b', bool)])

        @DeltaBlock(outputs=[('a', int), ('b', bool)])
        def add_1_true(n: int):
            return n+1, True

        with DeltaGraph() as graph:
            forked_input = add_1_true(n=5)
            template_2.call(a=forked_input.a, b=forked_input.b)

        self.assertTrue(graph.check())

    def test_multi_output(self):
        """Test that a multi-output pure template is allowed
        """
        template_o = NodeTemplate(outputs=[('a', int), ('b', bool)])
        template_i = NodeTemplate(inputs=[('a', int), ('b', bool)])

        with DeltaGraph() as graph:
            forked_input = template_o.call()
            template_i.call(a=forked_input.a, b=forked_input.b)

        self.assertTrue(graph.check())

    def test_placeholder_input(self):
        template_3 = NodeTemplate(inputs=[('a', int)])

        with DeltaGraph() as graph:
            a = placeholder_node_factory()
            template_3.call(a=a)

        a.specify_by_func(self.func_for_placeholder)
        self.assertTrue(graph.check())

    def test_partial_arg_types(self):
        template_4 = NodeTemplate(inputs=[('a', int), ('b', bool)])

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
        template_1 = NodeTemplate(inputs=[('a', bool)])

        with self.assertRaises(DeltaTypeError):
            with DeltaGraph() as graph:
                template_1.call(a=add_const(1, 2))
            graph.check()


class OpCacher2():

    def __init__(self):
        self._add_cache = {}

    @DeltaMethodBlock()
    def cached_add(self, n1: int, n2: int) -> int:
        if (a, b) in self._add_cache:
            return self._add_cache[(a, b)]
        else:
            result = a+b
            self._add_cache[(a, b)] = result
            return result


class NoBodyAddBodyTest(unittest.TestCase):
    """Tests for when the default call is used to create a node with no bodies
    and then ``add_body`` is used to give the node a body.
    """

    def test_add_func(self):
        test_template1 = NodeTemplate(name="test_1",
                                      inputs=[('n1', int), ('n2', int)],
                                      outputs=[('output', int)])

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 0)
        n1.add_body(add_non_const)
        self.assertEqual(len(n1.bodies), 1)
        self.assertIn('add_non_const', n1.body.access_tags)

    def test_add_method(self):
        test_template1 = NodeTemplate(name="test_1",
                                      inputs=[('n1', int), ('n2', int)],
                                      outputs=[('output', int)])
        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 0)
        n1.add_body(OpCacher2().cached_add)
        self.assertEqual(len(n1.bodies), 1)
        self.assertIn('cached_add', n1.body.access_tags)

    def test_add_multiple(self):
        test_template1 = NodeTemplate(name="test_1",
                                      inputs=[('n1', int), ('n2', int)],
                                      outputs=[('output', int)])

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 0)
        n1.add_body(OpCacher2().cached_add)
        n1.add_body(add_non_const)
        self.assertEqual(len(n1.bodies), 2)
        self.assertIn('cached_add', n1.body.access_tags)

    def test_add_interactive(self):
        test_template1 = NodeTemplate(name="test_1",
                                      inputs=[('n1', int), ('n2', int)],
                                      outputs=[('output', int)])

        @Interactive(inputs=[('n1', int), ('n2', int)],
                     outputs=[('output', int)])
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
            inputs=[('a', Optional(int)), ('b', Optional(int))]
        )

        class AMigenNode(MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', Optional(int))
                template.add_pa_in_port('b', Optional(int))

        with DeltaGraph():
            n1 = test_template1.call(a=2, b=3)

        self.assertEqual(len(n1.bodies), 0)
        n1.add_body(AMigenNode())
        self.assertEqual(len(n1.bodies), 1)
        self.assertIn(PyMigenBody, n1.body.access_tags)

    def test_add_invalid_body(self):
        test_template1 = NodeTemplate(name="test_1",
                                      inputs=[('a', int), ('b', int)],
                                      outputs=[('output', int)])

        @DeltaBlock(allow_const=False)
        def simple_add_to_bool(a: int, b: int) -> bool:
            return bool(a + b)

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        with self.assertRaises(ValueError):
            n1.add_body(simple_add_to_bool)


if __name__ == "__main__":
    unittest.main()
