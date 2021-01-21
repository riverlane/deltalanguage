"""Testing various functionality of output splitting and how DeltaPySimulator
adds splitter nodes if needed.
"""

import unittest

from test._utils import (add_non_const, add1_or0,
                         return_12, return_12_non_const)

from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator, DeltaQueue
from deltalanguage.wiring import (DeltaBlock, DeltaGraph,
                                  placeholder_node_factory)


@DeltaBlock(allow_const=True)
def return_1() -> int:
    return 1


@DeltaBlock(allow_const=False)
def return_1_non_const() -> int:
    return 1


@DeltaBlock(allow_const=True)
def increment(val: int) -> int:
    return val + 1


@DeltaBlock(allow_const=False)
def increment_non_const(val: int) -> int:
    return val + 1


class SplittingTest(unittest.TestCase):
    """Testing how DeltaPySimulator adds splitter nodes."""

    def setUp(self):
        r"""Build the graph
        ```
                     / saver1
                    /
            return_1 -- saver2
                    \
                     \ saver3
        ```
        """
        with DeltaGraph() as my_graph:
            saver1 = StateSaver(int)
            saver2 = StateSaver(int)
            saver3 = StateSaver(int)

            val = return_1()
            saver1.save(val)
            saver2.save(val)
            saver3.save(val)

        self.graph = my_graph
        self.savers = [saver1, saver2, saver3]

    def test_split_nodes(self):
        """Test that there is the correct number of nodes _before_
        and _after_ the runtime adds any splitter nodes.
        """
        self.assertEqual(len(self.graph.nodes), len(self.savers) + 1)
        DeltaPySimulator(self.graph)
        self.assertEqual(len(self.graph.nodes), len(self.savers) + 2)

    def test_queues(self):
        """Test that the queues out of the splitter node are DeltaQueues."""
        splitter_node = self.graph.find_node_by_name("splitter")
        self.assertTrue(splitter_node is None)

        runtime = DeltaPySimulator(self.graph)
        splitter_node = self.graph.find_node_by_name("splitter")
        out_qs = runtime.out_queues[splitter_node.name]

        self.assertEqual(len(out_qs), 3)
        for q in out_qs.values():
            self.assertIsInstance(q, DeltaQueue)

    def test_graph_properties(self):
        self.graph.check()
        self.graph.do_automatic_splitting()
        self.graph.check()


class SplittingWithPlaceholderNodeTest(unittest.TestCase):
    """Testing how DeltaPySimulator adds splitter nodes if the graph is
    created with placeholders."""

    def setUp(self):
        r"""Build the graph
        ```
                     / saver1
                    /
            placeholder -- saver2
                    \
                     \ saver3
        ```
        """
        with DeltaGraph() as my_graph:
            saver1 = StateSaver(bool)
            saver2 = StateSaver(bool)
            saver3 = StateSaver(bool)

            val = placeholder_node_factory()
            saver1.save(val)
            saver2.save(val)
            saver3.save(val)

            def true() -> bool:
                return True

            val.specify_by_func(true)

        self.graph = my_graph
        self.savers = [saver1, saver2, saver3]

    def test_split_nodes(self):
        """Test that there is the correct number of nodes _before_
        and _after_ the runtime adds any splitter nodes.
        """
        self.assertEqual(len(self.graph.nodes), len(self.savers) + 1)
        DeltaPySimulator(self.graph)
        self.assertEqual(len(self.graph.nodes), len(self.savers) + 2)

    def test_queues(self):
        """Test that the queues out of the splitter node are DeltaQueues."""
        splitter_node = self.graph.find_node_by_name("splitter")
        self.assertTrue(splitter_node is None)

        runtime = DeltaPySimulator(self.graph)
        splitter_node = self.graph.find_node_by_name("splitter")
        out_qs = runtime.out_queues[splitter_node.name]

        self.assertEqual(len(out_qs), 3)
        for q in out_qs.values():
            self.assertIsInstance(q, DeltaQueue)

    def test_graph_properties(self):
        self.graph.check()
        self.graph.do_automatic_splitting()
        self.graph.check()


class SplittingForkedTest(unittest.TestCase):
    """Testing how DeltaPySimulator adds splitter nodes for a graph with
    forked return."""

    def setUp(self):
        r"""Build the graph
        ```
                     / saver1
                    /
            placeholder -- saver2
                    \
                     \ saver3
        ```
        """
        with DeltaGraph() as my_graph:
            saver1 = StateSaver(int)
            saver2 = StateSaver(int)
            saver3 = StateSaver(int)

            val = return_12()
            saver1.save(val=val.x)
            saver2.save(val=val.x)
            saver3.save(val=val.y)

        self.graph = my_graph
        self.savers = [saver1, saver2, saver3]

    def test_split_nodes(self):
        """Test that there is the correct number of nodes _before_
        and _after_ the runtime adds any splitter nodes.
        """
        self.assertEqual(len(self.graph.nodes), len(self.savers) + 1)
        DeltaPySimulator(self.graph)
        self.assertEqual(len(self.graph.nodes), len(self.savers) + 2)

    def test_queues(self):
        """Test that the queues out of the splitter node are DeltaQueues."""
        splitter_node = self.graph.find_node_by_name("splitter")
        self.assertTrue(splitter_node is None)

        runtime = DeltaPySimulator(self.graph)
        splitter_node = self.graph.find_node_by_name("splitter")
        out_qs = runtime.out_queues[splitter_node.name]

        self.assertEqual(len(out_qs), 2)
        for q in out_qs.values():
            self.assertIsInstance(q, DeltaQueue)

    def test_graph_properties(self):
        self.graph.check()
        self.graph.do_automatic_splitting()
        self.graph.check()


class ForkedReturnIntegratedTest(unittest.TestCase):
    """Run graphs with a forked return node in constant and non-constant mode.
    """

    def test_forked_return_const_to_const(self):
        """Constant node w/ forked return -> constant -> exit."""
        s = StateSaver(int)
        with DeltaGraph() as graph:
            val = return_12()
            s.save_and_exit(increment(val.x))

        DeltaPySimulator(graph).run()
        self.assertEqual(s.saved, [2])

    def test_forked_return_const_to_non_const(self):
        """Constant node w/ forked return -> non-constant -> exit."""
        s = StateSaver(int)
        with DeltaGraph() as graph:
            val = return_12()
            s.save_and_exit(increment_non_const(val.x))

        DeltaPySimulator(graph).run()
        self.assertEqual(s.saved, [2])

    def test_forked_return_non_const_to_non_const(self):
        """Non-constant node w/ forked return -> non-constant -> exit."""
        s = StateSaver(int)
        with DeltaGraph() as graph:
            val = return_12_non_const()
            s.save_and_exit(increment_non_const(val.x))

        DeltaPySimulator(graph).run()
        self.assertEqual(s.saved, [2])


class SplittingIntegratedTest(unittest.TestCase):
    """Run graphs with various configuration of splitting of
    constant and non-constant nodes.
    """

    def test_splitting_to_one_node_const(self):
        """Splitted output of a constant node and sent to another node's
        different inputs."""
        s = StateSaver(int)
        with DeltaGraph() as graph:
            val = return_1()
            s.save_and_exit(add_non_const(val, val))

        DeltaPySimulator(graph).run()
        self.assertEqual(s.saved, [2])

    def test_splitting_to_one_node_non_const(self):
        """Splitted output of a non-constant node and sent to another node's
        different inputs."""
        s = StateSaver(int)
        with DeltaGraph() as graph:
            val = return_1_non_const()
            s.save_and_exit(add_non_const(val, val))

        DeltaPySimulator(graph).run()
        self.assertEqual(s.saved, [2])

    def test_splitting_of_one_forked_const(self):
        """One of forked outputs of a constant node is splitted."""
        s1 = StateSaver(int)
        s2 = StateSaver(int)
        with DeltaGraph() as graph:
            val = return_12()
            val_x = val.x
            s1.save(val_x)
            s2.save_and_exit(val_x)

        rt = DeltaPySimulator(graph)
        rt.run()
        self.assertEqual(s2.saved, [1])

    def test_splitting_of_one_forked_non_const(self):
        """One of forked outputs of a non-constant node is splitted."""
        s1 = StateSaver(int)
        s2 = StateSaver(int)
        with DeltaGraph() as graph:
            val = return_12_non_const()
            val_x = val.x
            s1.save(val_x)
            s2.save_and_exit(val_x)

        rt = DeltaPySimulator(graph)
        rt.run()
        self.assertEqual(s2.saved, [1])

    def test_splitting_of_multiple_forked_const(self):
        """Multiple forked outputs of a constant node are splitted."""
        s = StateSaver(int)
        with DeltaGraph() as graph:
            val = return_12()
            s.save_and_exit(
                add_non_const(
                    add_non_const(
                        add_non_const(
                            val.x,
                            val.x
                        ),
                        val.y),
                    val.y
                )
            )

        DeltaPySimulator(graph).run()
        self.assertEqual(s.saved, [6])

    def test_splitting_of_multiple_forked_non_const(self):
        """Multiple forked outputs of a non-constant node are splitted."""
        s = StateSaver(int)
        with DeltaGraph() as graph:
            val = return_12_non_const()
            s.save_and_exit(
                add_non_const(
                    add_non_const(
                        add_non_const(
                            val.x,
                            val.x
                        ),
                        val.y),
                    val.y
                )
            )

        DeltaPySimulator(graph).run()
        self.assertEqual(s.saved, [6])


if __name__ == "__main__":
    unittest.main()
