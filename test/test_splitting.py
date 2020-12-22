"""Testing various funtionality of output splitting and how DeltaPySimulator
adds splitter nodes if needed.
"""

import unittest

from test._utils import return_1, return_12

from deltalanguage.lib import make_state_saver
from deltalanguage.runtime import DeltaPySimulator, DeltaQueue
from deltalanguage.wiring import DeltaGraph, placeholder_node_factory


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
            saver1 = make_state_saver(int)
            saver2 = make_state_saver(int)
            saver3 = make_state_saver(int)

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
            saver1 = make_state_saver(bool)
            saver2 = make_state_saver(bool)
            saver3 = make_state_saver(bool)

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
            saver1 = make_state_saver(int)
            saver2 = make_state_saver(int)
            saver3 = make_state_saver(int)

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


if __name__ == "__main__":
    unittest.main()
