"""Testing how constant nodes, such as PyConstNode, are created.
"""

import unittest

from test._utils import (printer,
                         return_12,
                         const_consumer,
                         add,
                         add_non_const,
                         return_2)

from deltalanguage.lib import StateSaver
from deltalanguage.wiring import (DeltaGraph,
                                  PyConstNode,
                                  PyFuncNode,
                                  PyMethodNode,
                                  is_needed)


class ConstFolding(unittest.TestCase):
    """Test that nodes are folded during graph construction."""

    def setUp(self):
        with DeltaGraph() as my_graph:
            n1 = add(4, 3)
            n2 = add_non_const(4, return_2())

        self.graph = my_graph
        self.folded = n1
        self.not_folded = n2

    def test_folded_is_const(self):
        self.assertIsInstance(self.folded, PyConstNode)

    def test_not_folded_is_not_const(self):
        self.assertIsInstance(self.not_folded, PyFuncNode)

    def test_graph_properties(self):
        self.graph.check()


class IsNeededTest(unittest.TestCase):
    """Test the is_needed function used in evaluating constant nodes at
    runtime.
    """

    def test_is_useful_simple(self):
        """One branch is not const -> source must be useful."""
        saver = StateSaver(int)

        with DeltaGraph():
            nums = return_12()
            s1 = saver.save(nums.x)
            p1 = printer(nums.y)

        self.assertIsInstance(nums, PyConstNode)
        self.assertIsInstance(s1, PyFuncNode)
        self.assertIsInstance(p1, PyFuncNode)

        self.assertTrue(is_needed(nums, (PyFuncNode, PyMethodNode)))

    def test_not_useful_simple(self):
        """Both branches are const -> source not useful."""
        with DeltaGraph():
            nums = return_12()
            p1 = const_consumer(nums.x)
            p2 = const_consumer(nums.y)

        self.assertIsInstance(nums, PyConstNode)
        self.assertIsInstance(p1, PyConstNode)
        self.assertIsInstance(p2, PyConstNode)

        self.assertFalse(is_needed(nums, (PyFuncNode, PyMethodNode)))

    def test_is_useful_complex(self):
        """One of the branches is a Method Node, making the source useful."""
        saver = StateSaver(int)

        with DeltaGraph():
            nums = return_12()

            p1 = printer(nums.x)
            _ = printer(nums.x)
            _ = printer(nums.x)
            _ = printer(nums.y)
            s1 = saver.save(nums.y)

        with self.subTest(msg="Test correct instancing"):
            self.assertIsInstance(p1, PyFuncNode)
            self.assertIsInstance(s1, PyFuncNode)

        with self.subTest(msg="Test source is needed"):
            self.assertTrue(is_needed(nums, (PyFuncNode, PyMethodNode)))

    def test_not_useful_complex(self):
        """None all the branches are const -> the source is not useful."""
        with DeltaGraph():
            nums = return_12()
            p1 = const_consumer(nums.x)
            _ = const_consumer(nums.x)
            _ = const_consumer(nums.y)
            _ = const_consumer(nums.y)

        self.assertIsInstance(p1, PyConstNode)
        self.assertFalse(is_needed(nums, (PyFuncNode, PyMethodNode)))


if __name__ == "__main__":
    unittest.main()
