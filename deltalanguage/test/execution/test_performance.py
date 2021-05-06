"""Collection of graphs, which we use to track performance of
runtimes and runtime simulators.

Note that performance benchmarks depend on hardware, thus if any of processing
units is updated the performance might benchmarks should too.

Proposed topics:

- time as metrics (MOVE from test_blocking.py)
  - speed tests with a lot of messages
  - how queue blocking work

- number of messages as metrics
  - we don't have them yet
"""

import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL


class TestExecutionPerformance(TestExecutionBaseDL):

    pass


if __name__ == "__main__":
    unittest.main()
