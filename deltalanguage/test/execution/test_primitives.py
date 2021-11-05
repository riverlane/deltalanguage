from tempfile import NamedTemporaryFile
import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL
from deltalanguage.test._node_lib import send_gates_list_then_exit


class TestExecutionPrimitives(TestExecutionBaseDL):
    """Execute graphs that use primitives defined in ``deltalanguage.lib``."""

    def test_state_saver_save_to_file(self):
        with NamedTemporaryFile(mode="w+") as f:
            store = dl.lib.StateSaver(int, filename=f.name)

            with dl.DeltaGraph() as graph:
                store.save_and_exit(1000)

            self.check_executes_graph(graph)

            f.seek(0)
            self.assertEqual(f.read(), "1000\n")

if __name__ == "__main__":
    unittest.main()
