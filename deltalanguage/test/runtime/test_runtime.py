"""Test DeltaPySimulator functionality pre-execution."""

import unittest

import deltalanguage as dl

from deltalanguage.test._graph_lib import (getg_const_chain,
                                           getg_optional_queues)


class DeltaQueueCreationTest(unittest.TestCase):
    """Test that the simulator creates queues properly."""

    def test_queue_types(self):
        """Test that queues of correct types are created (or not) depending on
        the type of the source and destination nodes.
        """
        graph = getg_const_chain()
        dl.DeltaPySimulator(graph)

        self.assertEqual(len(graph.nodes[0].out_queues), 0)
        self.assertEqual(len(graph.nodes[1].out_queues), 1)
        self.assertEqual(len(graph.nodes[2].out_queues), 1)

        self.assertEqual(type(graph.nodes[1].out_queues['output']),
                         dl.runtime.ConstQueue)
        self.assertEqual(type(graph.nodes[2].out_queues['output']),
                         dl.runtime.DeltaQueue)

    def test_queue_optionality(self):
        """Test that queues inhere correct optionality depending on the type of
        the destination node.
        """
        graph = getg_optional_queues()
        dl.DeltaPySimulator(graph)

        self.assertEqual(graph.nodes[0].out_queues['output'].optional, True)
        self.assertEqual(graph.nodes[1].out_queues['output'].optional, False)


if __name__ == "__main__":
    unittest.main()
