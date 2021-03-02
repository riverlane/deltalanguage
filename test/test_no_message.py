"""Testing Void behaviour.
"""

import unittest

import deltalanguage as dl

from test._utils import printer


class VoidTest(unittest.TestCase):

    def test_error_thrown(self):
        """Nodes without output ports cannot produce output.

        .. note::
            This is very different from python's functions that return None
            by default.
        """
        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                no_message = printer(5)
                printer(no_message)


if __name__ == "__main__":
    unittest.main()
