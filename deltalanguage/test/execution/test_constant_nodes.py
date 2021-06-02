"""Execute graphs with constant nodes, which are pre-evaluated beforehand.
"""

import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL
from deltalanguage.test._graph_lib import (getg_const_chain,
                                           getg_optional_const)


class TestExecutionConstantNodes(TestExecutionBaseDL):

    def test_simple_chain(self):
        """Test 3 types of communication links:
        - from constant to constant nodes
        - from constant to non-constant nodes
        - from non-constant to non-constant nodes
        """
        graph = getg_const_chain()
        self.check_executes_graph(graph, "saving 2\n")

    def test_const_nodes_and_optional(self):
        """Testing that a constant node _always_ provides messages, even if
        the receiving port is optional.
        """
        graph = getg_optional_const()
        self.check_executes_graph(graph, "saving 2000\n")

    def test_exit_const_node(self):
        """DeltaRuntimeExit cannot be raised in a constant node."""
        @dl.DeltaBlock(allow_const=True)
        def const_save_exit(n: int):
            raise dl.DeltaRuntimeExit

        with dl.DeltaGraph() as graph:
            const_save_exit(1)

        self.check_executes_graph(graph, exception=RuntimeError)


if __name__ == "__main__":
    unittest.main()
