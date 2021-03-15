import unittest
from collections import OrderedDict

from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  DeltaMethodBlock,
                                  MigenNodeTemplate,
                                  NodeTemplate,
                                  Interactive,
                                  RealNode)
from deltalanguage.data_types import DOptional
from deltalanguage.wiring._node_classes.node_bodies import PyMigenBody


test_template1 = NodeTemplate(name="AdderTemplate",
                              in_params=OrderedDict([('a', int), ('b', int)]),
                              out_type=int)


@DeltaBlock(test_template1, allow_const=False)
def simple_add(a: int, b: int) -> int:
    return a + b


@DeltaBlock(test_template1, allow_const=False)
def over_complex_add(a: int, b: int) -> int:
    return 2*a + 2*b - a - b


@Interactive(template=test_template1,
             in_params=OrderedDict([('a', int), ('b', int)]),
             out_type=int)
def broken_adder(node: RealNode):
    a = node.receive('a')
    b = node.receive('b')
    node.send(a+b+1)


class OpCacher():

    def __init__(self):
        self._add_cache = {}

    @DeltaMethodBlock(test_template1)
    def cached_add(self, a: int, b: int) -> int:
        if (a, b) in self._add_cache:
            return self._add_cache[(a, b)]
        else:
            result = a+b
            self._add_cache[(a, b)] = result
            return result


class NodeTempalteViaDecoratorsTest(unittest.TestCase):
    """Tests for the NodeTemplate and its use in associating multiple
    constructors/bodies together.
    """

    def test_via_DeltaBlock(self):
        saver = StateSaver()
        with DeltaGraph() as graph:
            n1 = simple_add(4, 3)
            saver.save_and_exit(n1)
        self.assertEqual(len(n1.bodies), 3)
        self.assertIn("simple_add", n1.body.access_tags)
        DeltaPySimulator(graph).run()
        self.assertEqual([7], saver.saved)

    def test_via_DeltaMethodBlock(self):
        saver = StateSaver()
        cacher = OpCacher()
        with DeltaGraph() as graph:
            n1 = cacher.cached_add(1, 3)
            saver.save_and_exit(n1)
        self.assertEqual(len(n1.bodies), 4)
        self.assertIn("cached_add", n1.body.access_tags)
        DeltaPySimulator(graph).run()
        self.assertEqual([4], saver.saved)

    def test_via_Interactive(self):
        saver = StateSaver()
        with DeltaGraph() as graph:
            n1 = broken_adder.call(a=1, b=3)
            saver.save_and_exit(n1)
        self.assertEqual(len(n1.bodies), 3)
        self.assertIn("broken_adder", n1.body.access_tags)
        DeltaPySimulator(graph).run()
        self.assertEqual([5], saver.saved)


m_template = NodeTemplate(name="MTemplate",
                          in_params=OrderedDict([('a', int), ('b', int)]),
                          out_type=int)


class AMigenNode(MigenNodeTemplate):
    def migen_body(self, template):
        template.add_pa_in_port('a', DOptional(int))
        template.add_pa_in_port('b', DOptional(int))


class NodeTemplateViaMigenClass(unittest.TestCase):
    """Test that migen body templates can be added to node templates
    using the migen node template constructor.
    """

    def test_via_migen_init(self):

        m_template = NodeTemplate(
            name="MTemplate",
            in_params=OrderedDict([('a', DOptional(int)),
                                   ('b', DOptional(int))])
        )

        @DeltaBlock(m_template, allow_const=False)
        def m_simple_add(a: DOptional(int), b: DOptional(int)):
            raise DeltaRuntimeExit

        m_maker = AMigenNode(node_template=m_template)
        with DeltaGraph():
            n1 = m_maker.call(a=1, b=3)
        self.assertEqual(len(n1.bodies), 2)
        self.assertIn(PyMigenBody, n1.body.access_tags)


class NodeTemplateTest(unittest.TestCase):
    """Some core behaviours of node templates tested
    """

    def test_multiple_nodes_same_template(self):
        """Test that the same NodeTemplate can be used to create
        multiple distinct nodes for the same graph.
        """
        saver = StateSaver()
        with DeltaGraph() as graph:
            n1 = over_complex_add(1, 3)
            n2 = simple_add(4, n1)
            saver.save_and_exit(n2)

        self.assertEqual(len(n1.bodies), 3)
        self.assertEqual(len(n2.bodies), 3)
        self.assertIn("over_complex_add", n1.body.access_tags)
        self.assertIn("simple_add", n2.body.access_tags)

        DeltaPySimulator(graph).run()
        self.assertEqual([8], saver.saved)

    def test_select_different_from_constructor(self):
        """Test that it is possible to select a different body than the
        one associated with the used constructor.
        """
        saver = StateSaver()
        with DeltaGraph() as graph:
            n1 = simple_add(1, 3)
            saver.save_and_exit(n1)

        graph.select_bodies(preferred=["broken_adder"])
        self.assertEqual(len(n1.bodies), 3)
        self.assertIn("broken_adder", n1.body.access_tags)

        DeltaPySimulator(graph).run()
        self.assertEqual([5], saver.saved)


class NodeTemplateDefaultCall(unittest.TestCase):
    """Tests for when the default call is used to create nodes with one or
    more bodies.

    .. note::
      See `test_no_body_node.py` for when default call is used to create nodes
      with no bodies.
    """

    def test_via_default_call(self):
        saver = StateSaver()
        with DeltaGraph() as graph:
            n1 = test_template1.call(9, 2)
            saver.save_and_exit(n1)
        self.assertEqual(len(n1.bodies), 3)
        self.assertIn("simple_add", n1.body.access_tags)
        DeltaPySimulator(graph).run()
        self.assertEqual([11], saver.saved)


class OpCacher2():

    def __init__(self):
        self._add_cache = {}

    @DeltaMethodBlock()
    def cached_add_2(self, a: int, b: int) -> int:
        if (a, b) in self._add_cache:
            return self._add_cache[(a, b)]
        else:
            result = a+b
            self._add_cache[(a, b)] = result
            return result


class AMigenNode2(MigenNodeTemplate):
    def migen_body(self, template):
        template.add_pa_in_port('a', DOptional(int))
        template.add_pa_in_port('b', DOptional(int))


class NodeTemplateAddConstructor(unittest.TestCase):
    """Tests for ``add_constructor`` method for adding new constructors
    to a ``NodeTemplate`` without re-defining the original constructor.
    """

    def test_add_func(self):
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(allow_const=False)
        def simple_add_2(a: int, b: int) -> int:
            return a + b

        test_template1.add_constructor(simple_add_2)

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 1)
        self.assertIn('simple_add_2', n1.body.access_tags)

    def test_add_method(self):
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(template=test_template1, allow_const=False)
        def simple_add_2(a: int, b: int) -> int:
            return a + b

        test_template1.add_constructor(OpCacher2.cached_add_2)

        with DeltaGraph():
            n1 = OpCacher2().cached_add_2(2, 3)

        self.assertEqual(len(n1.bodies), 2)
        self.assertIn('cached_add_2', n1.body.access_tags)

    def test_add_interactive(self):
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @Interactive(in_params=OrderedDict([('a', int), ('b', int)]),
                     out_type=int)
        def broken_adder_2(node: RealNode):
            a = node.receive('a')
            b = node.receive('b')
            node.send(a+b+1)

        test_template1.add_constructor(broken_adder_2)

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 1)
        self.assertIn('broken_adder_2', n1.body.access_tags)

    def test_add_migen(self):
        test_template1 = NodeTemplate(
            name="test_1",
            in_params=OrderedDict([('a', DOptional(int)),
                                   ('b', DOptional(int))])
        )

        test_template1.add_constructor(AMigenNode2())

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 1)
        self.assertIn(PyMigenBody, n1.body.access_tags)

    def test_add_with_existing_other_template(self):
        """Test for when the constructor we are adding is already associated
        with some other ``NodeTemplate``.
        """
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        test_template2 = NodeTemplate(name="test_2",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(test_template2, allow_const=False)
        def simple_add_2(a: int, b: int) -> int:
            return a + b

        test_template1.add_constructor(simple_add_2)

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 1)
        self.assertIn('simple_add_2', n1.body.access_tags)

    def test_add_with_existing_same_template(self):
        """Test for when the constructor we are adding is already on the
        ``NodeTemplate``. The constructor should not be added twice.
        """
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(test_template1, allow_const=False)
        def simple_add_2(a: int, b: int) -> int:
            return a + b

        test_template1.add_constructor(simple_add_2)

        with DeltaGraph():
            n1 = test_template1.call(2, 3)

        self.assertEqual(len(n1.bodies), 1)
        self.assertIn('simple_add_2', n1.body.access_tags)

    def test_add_invalid_constructor(self):
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(allow_const=False)
        def simple_add_to_bool(a: int, b: int) -> bool:
            return bool(a + b)

        with self.assertRaises(ValueError):
            test_template1.add_constructor(simple_add_to_bool)


class InvalidNodeTemplate(unittest.TestCase):
    """Test that errors are raised when node templates
    are created in some way that is invalid.
    """

    def test_in_params_enforced(self):
        """Test to ensure in params must match when associating
        constructors with a NodeTemplate
        """
        test_template2 = NodeTemplate(name="test",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        with self.assertRaises(ValueError):
            @DeltaBlock(test_template2, allow_const=False)
            def _test1(a: int, b: bool) -> int:
                return a + b

        with self.assertRaises(ValueError):
            @DeltaBlock(test_template2, allow_const=False)
            def _test2(wrong_name: int, b: int) -> int:
                return wrong_name + b

    def test_in_params_enforced_optional(self):
        """Test to ensure in params must match when associating
        constructors with a NodeTemplate
        """
        test_template2 = NodeTemplate(
            name="test",
            in_params=OrderedDict(
                [('a', DOptional(int)), ('b', DOptional(int))]),
            out_type=int
        )

        with self.assertRaises(ValueError):
            @DeltaBlock(test_template2, allow_const=False)
            def _test1(a: DOptional(int), b: int) -> int:
                return a + b

        with self.assertRaises(ValueError):
            @ DeltaBlock(test_template2, allow_const=False)
            def _test2(wrong_name: int, b: int) -> int:
                return wrong_name + b

    def test_out_type_enforced(self):
        """Test to ensure out type must match when associating
        constructors with a NodeTemplate
        """
        test_template2 = NodeTemplate(name="test",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        with self.assertRaises(ValueError):
            @DeltaBlock(test_template2, allow_const=False)
            def _test1(a: int, b: int) -> bool:
                return a + b


class NodeTemplateMerge(unittest.TestCase):
    """Test that node templates can be merged correctly or raise errors when
    merge is not appropriate.
    """

    def __init__(self, methodName):
        super().__init__(methodName)
        test_template1 = NodeTemplate(name="test_1",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(test_template1, allow_const=False)
        def simple_add(a: int, b: int) -> int:
            return a + b

        self.template_1_body = simple_add.template
        self.test_template1 = test_template1

    def test_merge_adds_bodies(self):
        """Test to ensure in params must match when associating
        constructors with a NodeTemplate.
        """
        test_template3 = NodeTemplate(name="test_3",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(test_template3, allow_const=False)
        def simple_add(a: int, b: int) -> int:
            return a + b

        test_template2 = NodeTemplate(name="test_2",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(test_template2, allow_const=False)
        def simple_add_2(a: int, b: int) -> int:
            return a + b

        test_template3.merge(test_template2)
        self.assertEqual(len(test_template3._body_templates), 2)
        self.assertIn(simple_add.template, test_template3._body_templates)
        self.assertIn(simple_add_2.template, test_template3._body_templates)

    def test_merge_use_in_graph(self):
        """Test to ensure in params must match when associating
        constructors with a NodeTemplate.
        """
        test_template3 = NodeTemplate(name="test_3",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(test_template3, allow_const=False)
        def simple_add(a: int, b: int) -> int:
            return a + b

        test_template2 = NodeTemplate(name="test_2",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=int)

        @DeltaBlock(test_template2, allow_const=False)
        def simple_add_2(a: int, b: int) -> int:
            return a + b

        test_template3.merge(test_template2)

        saver = StateSaver()
        with DeltaGraph() as graph:
            n1 = simple_add_2(4, 73)
            saver.save_and_exit(n1)

        self.assertEqual(len(n1.bodies), 2)

        graph.select_bodies(preferred=['simple_add'])
        self.assertIn("simple_add", n1.body.access_tags)
        DeltaPySimulator(graph).run()
        self.assertEqual([77], saver.saved)

    def test_in_params_enforced_merge(self):
        """Test to ensure in params must match when associating
        constructors with a NodeTemplate.
        """
        test_template2 = NodeTemplate(name="test_2",
                                      in_params=OrderedDict(
                                          [('a', int), ('c', int)]),
                                      out_type=int)

        with self.assertRaises(ValueError):
            self.test_template1.merge(test_template2)

        with self.assertRaises(ValueError):
            test_template2.merge(self.test_template1)

    def test_out_type_enforced_merge(self):
        """Test to ensure in params must match when associating
        constructors with a NodeTemplate.
        """
        test_template2 = NodeTemplate(name="test_2",
                                      in_params=OrderedDict(
                                          [('a', int), ('b', int)]),
                                      out_type=bool)

        with self.assertRaises(ValueError):
            self.test_template1.merge(test_template2)

        with self.assertRaises(ValueError):
            test_template2.merge(self.test_template1)

    def test_self_merge(self):
        """Test to ensure merge self does not result in odd behaviour."""
        self.test_template1.merge(self.test_template1)
        self.assertEqual(len(self.test_template1._body_templates), 1)
        self.assertIn(self.template_1_body,
                      self.test_template1._body_templates)


if __name__ == "__main__":
    unittest.main()
