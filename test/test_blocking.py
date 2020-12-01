"""Testing that limiting in port sizes results in thread blocking.
"""

import datetime
import time
import unittest

from deltalanguage.data_types import DInt, NoMessage
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import (py_node_factory,
                                  DeltaGraph,
                                  Interactive,
                                  PyInteractiveNode)

time_diff = None


@Interactive({}, int, name="send_and_check_time")
def send_and_check_time(node: PyInteractiveNode):
    """Send enough messages that we block ourselves, and then noting how long
    it takes to send the final message.
    """
    node.send(1)
    node.send(2)
    t1 = datetime.datetime.now()
    node.send(3)
    t2 = datetime.datetime.now()
    global time_diff
    time_diff = t2-t1
    raise DeltaRuntimeExit


def receive_then_sleep(n: int):
    """Receive a message, then wait for a second."""
    time.sleep(1)


class TestBlocking(unittest.TestCase):

    def test_blocking(self):
        """Test that our process was blocked.
        Note that we only care that our thread was blocked for some time,
        not that it was blocked for a second. This is because depending on
        timing or delays, the block might be more or less than a second.
        So we only block for half a second to be safe.
        """
        with DeltaGraph() as test_graph:
            n = send_and_check_time.call()
        py_node_factory(test_graph,
                        False,
                        node_func=receive_then_sleep,
                        in_params={'n': DInt()},
                        out_type=NoMessage,
                        in_port_size=1,
                        n=n)
        rt = DeltaPySimulator(test_graph)
        rt.run()
        self.assertGreaterEqual(
            time_diff, datetime.timedelta(milliseconds=500))


if __name__ == "__main__":
    unittest.main()
