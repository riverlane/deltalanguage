"""Testing wiring of the graph."""

import unittest

import deltalanguage as dl

from deltalanguage.test._node_lib import terminate_non_const


class NoOutputTest(unittest.TestCase):

    def test_error_thrown(self):
        """Nodes without output ports cannot produce output.

        .. note::
            This is very different from python's functions that return None
            by default.
        """
        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                no_message = terminate_non_const(5)
                terminate_non_const(no_message)


if __name__ == "__main__":
    unittest.main()
