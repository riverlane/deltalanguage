import io
import textwrap
import unittest
import unittest.mock

import deltalanguage as dl


# True if DeltaPySimulator is used
PYSIMULATOR = True


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
    def check_executes(self, graph, expect, mock_stdout):
        """DeltaPySimulator executes the graph execution.

        Parameters
        ----------
        expect : str
            Should contain the exact multistring expression we expect on
            stdout, excluding both Python prefix and postfix.
        mock_stdout
            ``unittest.mock`` captures stdout and refers to this object.
        """
        dl.DeltaPySimulator(graph).run()

        if expect:
            self.assertMultiLineEqual(
                mock_stdout.getvalue(),
                self.python_output_prefix +
                textwrap.dedent(expect) +
                self.python_output_suffix
            )

    def check_executes_graph(self, graph, expect=None, files=None, reqs=None):
        """Main checking routine that should be overwritten when for
        testting of other simulators and runtime simulators.
        """
        self.check_executes(graph, expect)
