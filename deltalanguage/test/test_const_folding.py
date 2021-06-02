"""Testing how nodes get turned to constant nodes, such as those with
a PyConstBody.

A node can be tagged with allow_contan==True, but it's not the only condition.
It's also important where this node takes the inputs from.
Below we consided these cases.

These tests do not test how the resulting graphs are executed, only
their construction.
"""

import unittest

from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  PyConstBody,
                                  PyFuncBody,
                                  NodeTemplate,
                                  placeholder_node_factory)

from deltalanguage.test._node_lib import (add_const,
                                          add_non_const,
                                          forward_const,
                                          forward_non_const,
                                          return_2_const,
                                          return_1_2_const)


class ConstFoldingTest(unittest.TestCase):
    """Test that single-bodies nodes are folded correctly during graph
    construction.
    """

    def test_simple_folding_const_inputs(self):
        """Test that nodes producing constants are constant nodes."""

        with DeltaGraph() as graph:
            n1 = add_const(4, 3)
            n2 = add_non_const(4, 2)

        # nodes producing constants are turned to constant nodes
        for node in graph.find_node_by_name('node'):
            self.assertIsInstance(node.body, PyConstBody)

        # this one is turned to a constant node as well
        self.assertIsInstance(n1.body, PyConstBody)

        # this one would have done so as well, but we disallowed it
        self.assertIsInstance(n2.body, PyFuncBody)

        self.assertTrue(graph.check())

    def test_simple_folding_non_const_inputs(self):
        """Test that nodes with non constant inputs cannot fold to become
        constant.
        """

        with DeltaGraph() as graph:
            n1 = add_const(4, forward_non_const(3))
            n2 = add_non_const(4, forward_non_const(2))

        # nodes producing constants are turned to constant nodes
        for node in graph.find_node_by_name('node'):
            self.assertIsInstance(node.body, PyConstBody)

        # this one is a non-constant one now
        self.assertIsInstance(n1.body, PyFuncBody)

        # this one is still a non-constant
        self.assertIsInstance(n2.body, PyFuncBody)

        self.assertTrue(graph.check())

    def test_simple_folding_chain(self):
        """Test that a chain of node tagged as constant will turn to
        constant nodes.
        """
        with DeltaGraph() as graph:
            n0 = return_2_const()
            n1 = forward_const(n0)
            n2 = forward_const(n1)

        self.assertIsInstance(n0.body, PyConstBody)
        self.assertIsInstance(n1.body, PyConstBody)
        self.assertIsInstance(n2.body, PyConstBody)

        self.assertTrue(graph.check())

    def test_simple_folding_chain_splitting(self):
        """Test that if an output of a constant node can be split between
        a constant and non-constan nodes, i.e. the source stays constant and
        only one of the destinations is constant.
        """
        with DeltaGraph() as graph:
            n0 = return_2_const()
            n1 = forward_const(n0)
            n2 = forward_const(n1)
            n3 = forward_non_const(n1)

        self.assertIsInstance(n0.body, PyConstBody)
        self.assertIsInstance(n1.body, PyConstBody)
        self.assertIsInstance(n2.body, PyConstBody)
        self.assertIsInstance(n3.body, PyFuncBody)

        self.assertTrue(graph.check())

    def test_forked_folding_all_const(self):
        """Check the case with a forked return.

        All the forked outputs go to const nodes ->
        source is a constant node as well.
        """
        with DeltaGraph():
            nums = return_1_2_const()
            p1 = forward_const(nums.x)
            p2 = forward_const(nums.y)

        self.assertIsInstance(nums.body, PyConstBody)
        self.assertIsInstance(p1.body, PyConstBody)
        self.assertIsInstance(p2.body, PyConstBody)

    def test_forked_folding_one_non_const(self):
        """Check the case with a forked return.

        One forked output goes to a non-const node ->
        the rest of destinations stay const.
        """
        with DeltaGraph() as graph:
            nums = return_1_2_const()
            p1 = forward_const(nums.x)
            p2 = forward_non_const(nums.y)

        self.assertIsInstance(nums.body, PyConstBody)
        self.assertIsInstance(p1.body, PyConstBody)
        self.assertIsInstance(p2.body, PyFuncBody)

        self.assertTrue(graph.check())

    def test_forked_folding_one_non_const_splitting(self):
        """Check the case with a forked return.

        Same as above but with splitting ->
        no funny business.
        """
        with DeltaGraph():
            nums = return_1_2_const()
            p1 = forward_const(nums.x)
            p2 = forward_non_const(nums.y)
            p3 = forward_const(nums.x)
            p4 = forward_const(nums.y)

        self.assertIsInstance(nums.body, PyConstBody)
        self.assertIsInstance(p1.body, PyConstBody)
        self.assertIsInstance(p2.body, PyFuncBody)
        self.assertIsInstance(p3.body, PyConstBody)
        self.assertIsInstance(p4.body, PyConstBody)


const_template = NodeTemplate(name="ConstFoldTestTemplate",
                              inputs=[('a', int)],
                              outputs=[('output', int)])


@DeltaBlock(template=const_template, allow_const=True)
def foo_const_1_t(a: int) -> int:
    return a


@DeltaBlock(template=const_template, allow_const=True)
def foo_const_2_t(a: int) -> int:
    return a


non_const_template = NodeTemplate(name="NonConstFoldTestTemplate",
                                  inputs=[('a', int)],
                                  outputs=[('output', int)])


@DeltaBlock(template=non_const_template, allow_const=False)
def foo_non_const_1_t(a: int) -> int:
    return a


@DeltaBlock(template=non_const_template, allow_const=False)
def foo_non_const_2_t(a: int) -> int:
    return a


semi_const_template = NodeTemplate(name="SemiConstFoldTestTemplate",
                                   inputs=[('a', int)],
                                   outputs=[('output', int)])


@DeltaBlock(template=semi_const_template, allow_const=False)
def foo_semi_const_1_t(a: int) -> int:
    return a


@DeltaBlock(template=semi_const_template, allow_const=True)
def foo_semi_const_2_t(a: int) -> int:
    return a


class ConstFoldingNodeTemplatesTest(unittest.TestCase):
    """Test that nodes created via multi-bodies NodeTemplates are folded
    correctly during graph construction."""

    def test_simple_folding_chain(self):
        """Test that a chain of node tagged as constant will turn to
        constant nodes.
        """
        with DeltaGraph() as graph:
            n0 = return_2_const()
            n1 = foo_const_1_t(n0)
            n2 = foo_const_2_t(n1)

        self.assertIsInstance(n0.body, PyConstBody)
        self.assertIsInstance(n1.body, PyConstBody)
        self.assertIsInstance(n2.body, PyConstBody)

        self.assertTrue(graph.check())

    def test_simple_folding_non_const_inputs(self):
        """Test that nodes with non constant inputs cannot fold to become
        constant.
        """

        with DeltaGraph() as graph:
            n1 = add_const(4, foo_non_const_1_t(3))
            n2 = add_non_const(4, foo_non_const_1_t(2))

        # nodes producing constants are turned to constant nodes
        for node in graph.find_node_by_name('node'):
            self.assertIsInstance(node.body, PyConstBody)

        # this one is a non-constant one now
        self.assertIsInstance(n1.body, PyFuncBody)

        # this one is still a non-constant
        self.assertIsInstance(n2.body, PyFuncBody)

        self.assertTrue(graph.check())

    def test_cannot_fold_through_semi_const_multi_body(self):
        """If a node has both constant and non-constant bodies, then
        this node cannot be folded.

        .. note::
          This behaviors might change so only the selected body
          (during execution) will define if the node can/cannot be
          folded.
        """

        with DeltaGraph() as graph:
            n1 = add_const(4, foo_semi_const_1_t(3))
            n2 = add_non_const(4, foo_semi_const_1_t(2))

        # nodes producing constants are turned to constant nodes
        for node in graph.find_node_by_name('node'):
            self.assertIsInstance(node.body, PyConstBody)

        # this one is a non-constant one now
        self.assertIsInstance(n1.body, PyFuncBody)

        # this one is still a non-constant
        self.assertIsInstance(n2.body, PyFuncBody)

        self.assertTrue(graph.check())


class ConstantNodeAndPlaceholderTest(unittest.TestCase):
    """Testing that a loop of constant nodes cannot be created via
    PlaceholderNode.
    """

    def test_specify_by_node(self):
        with DeltaGraph() as graph:
            p = placeholder_node_factory()
            b = forward_const(p)
            p.specify_by_node(forward_const(b))

        for node in graph.nodes:
            self.assertIsInstance(node.body, PyFuncBody)

    def test_specify_by_func(self):
        def forward_func(val: int) -> int:
            return val

        with DeltaGraph() as graph:
            p_1 = placeholder_node_factory()
            p_2 = placeholder_node_factory(p_1)
            p_1.specify_by_node(forward_const(p_2))
            p_2.specify_by_func(forward_func, allow_const=True)

        for node in graph.nodes:
            self.assertIsInstance(node.body, PyFuncBody)

    def test_const_selfloop(self):
        with DeltaGraph() as graph:
            p = placeholder_node_factory()
            p.specify_by_node(forward_const(p))

        for node in graph.nodes:
            self.assertIsInstance(node.body, PyFuncBody)


if __name__ == "__main__":
    unittest.main()
