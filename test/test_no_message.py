"""Testing NoMessage behaviour.
"""

import unittest

from test._utils import printer

from deltalanguage.lib import StateSaver, make_generator
from deltalanguage.runtime import DeltaPySimulator
from deltalanguage.wiring import DeltaGraph


class NoMessageTestSimple(unittest.TestCase):
    """Check that raise NoMessage can be used if a node does not send a
    message with a specific condition. Here only even numbers can go through.
    """

    def test_correct_result(self):
        s1 = StateSaver(int, condition=lambda x: x % 2 == 0)
        s2 = StateSaver(int, condition=lambda x: x == 0)
        l = [1, 3, 7, 2, 5, 4, 9, 0, -1, 8]
        sender = make_generator(l)

        with DeltaGraph() as graph:
            only_even = s1.transfer_if(sender.call())
            s2.save_and_exit_if(only_even)

        rt = DeltaPySimulator(graph)
        rt.run()

        self.assertEqual(s1.saved, l)
        self.assertEqual(s2.saved, [2, 4, 0])


class NoMessageCannotBeOutput(unittest.TestCase):

    def test_error_thrown(self):
        with self.assertRaises(ValueError):
            with DeltaGraph():
                no_message = printer(5)
                printer(no_message)


if __name__ == "__main__":
    unittest.main()
