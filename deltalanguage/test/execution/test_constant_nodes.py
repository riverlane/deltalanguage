"""Execute graphs with constant nodes, which are pre-evaluated beforehand.

- TODO move tests from test_runtime.py
- data is passed successfully between constant nodes
- exit from constant nodes is forbidden
- TODO check test_const_folding.py and move tests here if needed
"""

import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL, PYSIMULATOR


class TestExecutionConstantNodes(TestExecutionBaseDL):

    pass
