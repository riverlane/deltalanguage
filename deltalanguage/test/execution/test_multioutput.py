"""Execute graphs with nodes that send outputs to multiple destinations."""

import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL
from deltalanguage.test._node_lib import (add_const,
                                          add_non_const,
                                          increment_const,
                                          increment_non_const,
                                          return_1_const,
                                          return_1_non_const,
                                          return_1_2_const,
                                          return_1_2_non_const)
from deltalanguage.test._graph_lib import (getg_splitting_const_const_same,
                                           getg_splitting_const_const_same_and_diff)


class TestExecutionSplittingSingleOutputNodeToSameNodeTest(TestExecutionBaseDL):
    """Execute graphs where a node with a single output reuses it
    for multiple destinations in the same node."""

    def test_splitting_const_const(self):
        """Const -> const -> exit."""
        graph = getg_splitting_const_const_same()
        self.check_executes_graph(graph, "saving 2\n")

    def test_splitting_const_non_const(self):
        """Const -> non-const -> exit."""
        s = dl.lib.StateSaver(int, verbose=True)
        with dl.DeltaGraph() as graph:
            val = return_1_const()
            s.save_and_exit(add_non_const(val, val))

        self.check_executes_graph(graph, "saving 2\n")

    def test_splitting_non_const_non_const(self):
        """Non-const -> non-const -> exit."""
        s = dl.lib.StateSaver(int, verbose=True)
        with dl.DeltaGraph() as graph:
            val = return_1_non_const()
            s.save_and_exit(add_non_const(val, val))

        self.check_executes_graph(graph, "saving 2\n")


class TestExecutionSplittingSingleOutputNodeToDiffNodesTest(TestExecutionBaseDL):
    """Execute graphs where a node with a single output reuses it
    for multiple destinations in different nodes."""

    def test_splitting_const_const(self):
        """Const -> const -> exit."""
        s = dl.lib.StateSaver(int, verbose=True)
        with dl.DeltaGraph() as graph:
            val = return_1_const()
            out = add_non_const(increment_const(val),
                                increment_const(val))
            s.save_and_exit(out)

        self.check_executes_graph(graph, "saving 4\n")

    def test_splitting_const_non_const(self):
        """Const -> non-const -> exit."""
        s = dl.lib.StateSaver(int, verbose=True)
        with dl.DeltaGraph() as graph:
            val = return_1_const()
            out = add_non_const(increment_non_const(val),
                                increment_non_const(val))
            s.save_and_exit(out)

        self.check_executes_graph(graph, "saving 4\n")

    def test_splitting_non_const_non_const(self):
        """Non-const -> non-const -> exit."""
        s = dl.lib.StateSaver(int, verbose=True)
        with dl.DeltaGraph() as graph:
            val = return_1_non_const()
            out = add_non_const(increment_non_const(val),
                                increment_non_const(val))
            s.save_and_exit(out)

        self.check_executes_graph(graph, "saving 4\n")


class TestExecutionSplittingMultiOutputNodeTest(TestExecutionBaseDL):
    """Execute graphs where a node with multiple outputs reuses them
    for multiple destinations both in the same or different nodes."""

    def test_splitting_const_const(self):
        graph = getg_splitting_const_const_same_and_diff()
        self.check_executes_graph(graph, "saving 6\n")

    def test_splitting_const_non_const(self):
        s = dl.lib.StateSaver(int, verbose=True)
        with dl.DeltaGraph() as graph:
            val = return_1_2_const()
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

        self.check_executes_graph(graph, "saving 6\n")

    def test_splitting_non_const_non_const(self):
        s = dl.lib.StateSaver(int, verbose=True)
        with dl.DeltaGraph() as graph:
            val = return_1_2_non_const()
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

        self.check_executes_graph(graph, "saving 6\n")


if __name__ == "__main__":
    unittest.main()
