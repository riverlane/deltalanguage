
import unittest

from deltalanguage.data_types import Optional, Tuple
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaMethodBlock,
                                  DeltaGraph,
                                  Interactive,
                                  PythonNode)
from deltalanguage.test._node_lib import TripleStateSaver


class ForkedSendTester:
    """Class that has a block method to return different tuples
    using different combinations of how blocks can output multiple returns
    """

    def __init__(self):
        self.line = 0

        self.outputs_dict = {
            1: (1, 2, False),
            2: None,
            3: (3, 4),
            4: 5,
            5: (6, None),
            6: (None, None, True),
            7: (7, None, False),
            8: 10,
        }

    @DeltaMethodBlock(outputs=[('x', int), ('y', int), ('z', bool)])
    def positional_send(self):
        self.line += 1
        if self.line in self.outputs_dict:
            return self.outputs_dict[self.line]


@DeltaBlock(outputs=[('x', int), ('y', int), ('z', bool)])
def too_many_positional():
    """Attempt to send too many returns out of a block
    """
    return 1, 2, False, 3


@DeltaBlock(outputs=[('x', Tuple([int, int])), ('y', int), ('z', bool)])
def tuple_first_alone():
    """Attempt to send too many returns out of a block
    """
    return 7, 7


class BlockSendBehaviourTest(unittest.TestCase):
    """Test the different ways an block body can return
    values when it has multiple outputs
    """

    def test_positional_block_send(self):
        ts = TripleStateSaver(11)
        fs = ForkedSendTester()

        with DeltaGraph() as graph:
            b_send = fs.positional_send()
            ts.multi_count_print_exit(b_send.x, b_send.y, b_send.z)

        DeltaPySimulator(graph).run()
        self.assertEqual(ts.x_store, [1, 3, 5, 6, 7, 10])
        self.assertEqual(ts.y_store, [2, 4])
        self.assertEqual(ts.z_store, [False, True, False])

    def test_too_many_positional(self):
        with DeltaGraph() as graph:
            too_many_positional()

        with self.assertRaises(RuntimeError):
            DeltaPySimulator(graph).run()

    def test_tuple_first_sending_alone(self):
        """Demonstration of how a user can run into an error when sending
        tuples as the first part of an output, and not specifing the other
        outputs.
        """
        with DeltaGraph() as graph:
            tuple_first_alone()

        with self.assertRaises(RuntimeError):
            DeltaPySimulator(graph).run()


if __name__ == "__main__":
    unittest.main()
