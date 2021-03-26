"""Collections of graphs which by running we check that the
basic components of DeltaGraph are supported and function properly.

Proposed topics that we can do to independent files
(in parenthesis we show where these tests are currently):

- graphs with nodes' bodies of all supported types (test_runtime.py)
  - PyFuncBody
  - PyMethodBody
  - PyInteractiveBody (test_interactive_node.py)
  - PyConstBody
  - PyMigenBody (all over the place, test_migen_interactive_comms.py,
    test_migen_node.py)

- nodes with optional ports (test_runtime.py)

- splitting of outputs (test_splitting.py)
  - same output to multiple destinations
  - forking output to multiple destinations

- constant nodes (test_runtime.py)
  - data is passed successfully between constant nodes
  - exit from constant nodes is forbidden

- graphs with multibody nodes where bodies are selected
  - afaik Deltasimulator does not support it yet and always uses the first body

- node_key tests (test_node_key.py)
  - i'm not sure Deltasimulator supports this

- all supported data types can be passed as messages.
"""

import unittest

import deltalanguage as dl

from deltalanguage.test._utils import add_non_const
from deltalanguage.test.execution.base import TestExecutionDLBase


class TestExecutionBasic(TestExecutionDLBase):
    """Example simplistic test."""

    def test_Int32(self):
        s = dl.lib.StateSaver(dl.Int(), verbose=True)
        with dl.DeltaGraph() as graph:
            s.save_and_exit(5)

        self.check_executes_graph(graph, "saving 5\n")

    def test_add(self):
        s = dl.lib.StateSaver(int, verbose=True)
        with dl.DeltaGraph() as graph:
            s.save_and_exit(add_non_const(2, 3))

        self.check_executes_graph(graph, "saving 5\n")


if __name__ == "__main__":
    unittest.main()
