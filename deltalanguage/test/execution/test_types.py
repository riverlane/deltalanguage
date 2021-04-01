import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL


class TestExecutionTypes(TestExecutionBaseDL):
    """Test that all supported data types can be passed as messages
    during ``DeltaGraph`` execution.

    TODO add more tests.
    """

    def test_Int(self):
        t = dl.Int(dl.Size(64))

        @dl.DeltaBlock()
        def foo() -> t:
            return 5

        s = dl.lib.StateSaver(t, verbose=True)

        with dl.DeltaGraph() as graph:
            s.save_and_exit(foo())

        self.check_executes_graph(graph, "saving 5\n")

    def test_Bool(self):
        t = dl.Bool()

        @dl.DeltaBlock()
        def foo() -> t:
            return True

        s = dl.lib.StateSaver(t, verbose=True)

        with dl.DeltaGraph() as graph:
            s.save_and_exit(foo())

        self.check_executes_graph(graph, "saving True\n")


if __name__ == "__main__":
    unittest.main()
