"""No need for execution tests here.

We want to make sure that the simulators/runtimes select bodies of multibody
nodes in the same way, use the same API.

- Deltasimulator does not support it yet and always uses the first body.
"""

import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL, PYSIMULATOR


class TestExecutionMultibodyNodes(TestExecutionBaseDL):

    pass
