"""We want to make sure that the simulators/runtimes select bodies of multibody
nodes in the same way, use the same API.
"""

import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL


class TestExecutionMultibodyNodes(TestExecutionBaseDL):

    def make_test_template(self):

        test_template = dl.NodeTemplate(
            name="TestTemplate",
            inputs=[('a', int), ('b', int)]
        )

        @dl.DeltaBlock(
            template=test_template,
            allow_const=False,
            tags=["exclude_me", "prefer_me"]
        )
        def func_1(a: int, b: int) -> dl.Void:
            print("func_1")
            raise dl.DeltaRuntimeExit

        @dl.DeltaBlock(
            template=test_template,
            allow_const=False
        )
        def func_2(a: int, b: int) -> dl.Void:
            print("func_2")
            raise dl.DeltaRuntimeExit

        @dl.DeltaBlock(
            template=test_template,
            allow_const=False,
            tags=["prefer_me"]
        )
        def func_3(a: int, b: int) -> dl.Void:
            print("func_3")
            raise dl.DeltaRuntimeExit

        return test_template

    def test_select_body_on_construction(self):
        """Test if single node bodies get their body auto-selected.
        Multi-body nodes do not undergo auto-selection.
        """
        with dl.DeltaGraph() as graph:
            n = self.make_test_template().call(1, 2)

        self.check_executes_graph(graph, expect="func_1\n")

    def test_execution_exclusion_preference(self):
        """Test that selection/execution works correctly with respect to body
        order, exclusions and preferences
        """

        with dl.DeltaGraph() as graph:
            n = self.make_test_template().call(1, 2)

        self.check_executes_graph(graph, expect="func_2\n",
                                  excluded_body_tags=["exclude_me"])

        self.check_executes_graph(graph, expect="func_3\n",
                                  excluded_body_tags=["exclude_me"],
                                  preferred_body_tags=["prefer_me"])

    def test_execution_fails_no_body(self):
        """Test that if all bodies are excluded an exception is raised when
        trying to run.
        """

        with dl.DeltaGraph() as graph:
            n = self.make_test_template().call(1, 2)

        excluded_body_tags = ["func_1", "func_2", "func_3"]
        self.check_executes_graph(graph, exception=RuntimeError,
                                  excluded_body_tags=excluded_body_tags)


if __name__ == "__main__":
    unittest.main()
