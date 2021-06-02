import unittest

import deltalanguage as dl

from deltalanguage.test._node_lib import (add_non_const,
                                          increment_const,
                                          increment_non_const,
                                          return_1_const,
                                          return_1_non_const,
                                          return_1_2_const,
                                          return_1_2_non_const,
                                          terminate_non_const)


class SplittingNodeTest(unittest.TestCase):
    """Testing automatic addition of splitter nodes at the output of
    nodes that reuse the same output for multiple destinations.
    """

    def test_const_node(self):
        """Constant node has one output reused multiple times."""
        with dl.DeltaGraph() as graph:
            output = return_1_const()
            terminate_non_const(output)
            terminate_non_const(output)
            terminate_non_const(output)

        self.assertTrue(graph.check())
        self.assertEqual(len(graph.nodes), 5)
        self.assertEqual(
            type(graph.find_node_by_name("return_1_const").body),
            dl.wiring.PyConstBody
        )
        self.assertEqual(type(graph.find_node_by_name("splitter").body),
                         dl.wiring.PyConstBody)

    def test_non_const_node(self):
        """Non-constant node has one output reused multiple times."""
        with dl.DeltaGraph() as graph:
            output = return_1_non_const()
            terminate_non_const(output)
            terminate_non_const(output)
            terminate_non_const(output)

        self.assertTrue(graph.check())
        self.assertEqual(len(graph.nodes), 5)
        self.assertEqual(
            type(graph.find_node_by_name("return_1_non_const").body),
            dl.wiring.PyFuncBody
        )
        self.assertEqual(type(graph.find_node_by_name("splitter").body),
                         dl.wiring.PyFuncBody)

    def test_non_const_node_via_placeholder(self):
        """Non-constant node created via a placeholder has one output reused
        multiple times."""
        with dl.DeltaGraph() as graph:
            output = dl.placeholder_node_factory()
            terminate_non_const(output)
            terminate_non_const(output)
            terminate_non_const(output)

            output.specify_by_node(return_1_non_const())

        self.assertTrue(graph.check())
        self.assertEqual(len(graph.nodes), 5)
        self.assertEqual(
            type(graph.find_node_by_name("return_1_non_const").body),
            dl.wiring.PyFuncBody
        )
        self.assertEqual(type(graph.find_node_by_name("splitter").body),
                         dl.wiring.PyFuncBody)

    def test_non_const_multioutput_node(self):
        """Non-constant node has one output of several(!) reused multiple
        times.
        """
        with dl.DeltaGraph() as graph:
            output = return_1_2_non_const()
            terminate_non_const(output.x)
            terminate_non_const(output.x)
            terminate_non_const(output.y)

        self.assertTrue(graph.check())
        self.assertEqual(len(graph.nodes), 5)
        self.assertEqual(
            type(graph.find_node_by_name("return_1_2_non_const").body),
            dl.wiring.PyFuncBody
        )
        self.assertEqual(type(graph.find_node_by_name("splitter").body),
                         dl.wiring.PyFuncBody)


class SplittingExceptionTest(unittest.TestCase):

    def test_non_split_fails_check(self):
        """If splitter nodes are not added for some reason, for instnance
        if the graph is hacked by Deltahackers, we raise an error.
        """
        with dl.DeltaGraph() as graph:
            output = return_1_non_const()
            terminate_non_const(output)
            terminate_non_const(output)
            terminate_non_const(output)

            # note: we are still in the "with" context
            with self.assertRaises(dl.data_types.DeltaIOError):
                graph.check()


if __name__ == "__main__":
    unittest.main()
