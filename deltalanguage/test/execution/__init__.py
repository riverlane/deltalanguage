"""Collection of tests that asserts consistency
across runtimes and runtime simulators by executing the same graphs and
checking their results.

The test cases contain a graph and an expected result, the methods defining
execution and comparison should be provided for each runtimes and
runtime simulator.

For testing Deltasimulator we suggest the following steps:
- import the test cases defined here
- subclass from them and overwrite method ``check_executes_graph``

The majority of tests already exist either in ``../runtime/``
or in the test suite for Deltasimulator in ``test_execution.py``.
"""


from .test_basic import (TestExecutionPyFuncBody,
                         TestExecutionPyInteractiveBody,
                         TestExecutionPyInteractiveBodySend,
                         TestExecutionPyMigenBody,
                         TestExecutionGeneral)
from .test_constant_nodes import TestExecutionConstantNodes
from .test_multibody_nodes import TestExecutionMultibodyNodes
from .test_multioutput import (
    TestExecutionSplittingSingleOutputNodeToSameNodeTest,
    TestExecutionSplittingSingleOutputNodeToDiffNodesTest,
    TestExecutionSplittingMultiOutputNodeTest
)
from .test_optional_inputs import TestExecutionOptionalInputs
from .test_performance import TestExecutionPerformance
from .test_primitives import TestExecutionPrimitives
from .test_types import TestExecutionTypes
