"""Execute graphs with nodes that send outputs to multiple destinations.

- TODO move more tests from test_splitting.py
"""

import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL
from deltalanguage.test._utils import add_non_const


class TestExecutionMultioutput(TestExecutionBaseDL):
    """Test nodes with multiple outputs."""

    def test_same_outputs(self):
        """The same output is sent to multiple destinations."""
        s = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph() as graph:
            n = add_non_const(2, 3)
            s.save_and_exit(add_non_const(n, n))

        self.check_executes_graph(graph, "saving 10\n")

    def test_different_outputs(self):
        """A node has multiple independent outputs."""
        @dl.DeltaBlock(outputs=[("a", int), ("b", int)], allow_const=False)
        def add_2_add_3(n: int):
            return n+2, n+3

        s = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph() as graph:
            ab = add_2_add_3(1)
            s.save_and_exit(add_non_const(ab.a, ab.b))

        self.check_executes_graph(graph, "saving 7\n")


if __name__ == "__main__":
    unittest.main()
