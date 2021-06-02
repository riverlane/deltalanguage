"""Execute graphs which have nodes with optional inputs, thus they are not
blocked on getting of input messages.
"""

import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL
from deltalanguage.test._graph_lib import getg_optional_queues


class TestExecutionOptionalInputs(TestExecutionBaseDL):

    def test_simple(self):
        """Test graph with a node that has both optional and non-optional
        inputs.
        """
        graph = getg_optional_queues()
        self.check_executes_graph(graph, "saving 2\n")


if __name__ == "__main__":
    unittest.main()
