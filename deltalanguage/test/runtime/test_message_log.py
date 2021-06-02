import logging
import unittest

import deltalanguage as dl

from deltalanguage.test._node_lib import (add_non_const,
                                          forward_non_const,
                                          return_1_const,
                                          return_2_const,
                                          TripleStateSaver)


class MessageLogTest(unittest.TestCase):
    """Test MessageLog.

    .. note::
        This is an execution test, but since this feature is implemented only
        for this simulator this test currently lives here instead of
        test/execution.
    """

    def setUp(self):
        s = dl.lib.StateSaver(int, condition=lambda x: x == 10)
        gen = dl.lib.make_generator(range(11))

        with dl.DeltaGraph() as self.test_graph:
            s.save_and_exit_if(forward_non_const(gen.call()))

    def test_clock_updates(self):
        """Messages should be displayed at end of run in logical clock order.
        """
        rt = dl.DeltaPySimulator(self.test_graph, msg_lvl=logging.DEBUG)
        rt.run()

        message_times = [msg.clk for node, _, msg in rt.msg_log.messages
                         if node.startswith("save")]

        self.assertGreater(len(message_times), 0)
        for time_1, time_2 in zip(message_times, message_times[1:]):
            self.assertLess(time_1, time_2)

    def test_no_message_logging(self):
        """Messages should not be logged at all if msg_lvl is not reset"""
        rt = dl.DeltaPySimulator(self.test_graph)
        rt.run()

        message_times = [msg.clk for node, _, msg in rt.msg_log.messages
                         if node.startswith("save")]

        self.assertEqual(message_times, [])


if __name__ == "__main__":
    unittest.main()
