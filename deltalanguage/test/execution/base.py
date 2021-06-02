import io
import textwrap
import unittest
import unittest.mock

import deltalanguage as dl


class TestExecutionBaseDL(unittest.TestCase):
    """Test execution base for Deltalanguage's ``DeltaPySimulator``,
    defines method for executing and checking test graphs.
    """

    def setUp(self):
        dl.DeltaGraph.clean_stack()
        self.files = []
        self.reqs = []
        self.maxDiff = None
        self.python_output_prefix = ""
        self.python_output_suffix = ""

    @unittest.mock.patch('sys.stdout', new_callable=io.StringIO)
    def check_executes(self, graph, expect, exception, mock_stdout,
                       excluded_body_tags=None, preferred_body_tags=None):
        """DeltaPySimulator executes the graph execution.

        Parameters
        ----------
        graph : dl.DeltaGraph
            The graph to execute.
        expect : str
            The exact multistring expression we expect on stdout
            (excluding any housekeeping messages).
        exception : Exception
            Exception thrown by a runtime/simulator at _any_ stage
            (includes building, deployment, execution, etc.).
        mock_stdout
            ``unittest.mock`` captures stdout and refers to this object.
        excluded_body_tags
            Body tags to exclude.
        preferred_body_tags
            Body tags to prefer.
        """
        graph.select_bodies(exclusions=excluded_body_tags,
                            preferred=preferred_body_tags)

        if exception:
            with self.assertRaises(exception):
                dl.DeltaPySimulator(graph).run()
        else:
            dl.DeltaPySimulator(graph).run()

        if expect:
            self.assertMultiLineEqual(
                mock_stdout.getvalue(),
                self.python_output_prefix +
                textwrap.dedent(expect) +
                self.python_output_suffix
            )

    def check_executes_graph(self, graph, expect=None, files=None, reqs=None,
                             exception=None, excluded_body_tags=None,
                             preferred_body_tags=None):
        """Main checking routine that should be overwritten when for
        testting of other simulators and runtime simulators.
        """
        self.check_executes(graph, expect, exception,
                            excluded_body_tags=excluded_body_tags,
                            preferred_body_tags=preferred_body_tags)
