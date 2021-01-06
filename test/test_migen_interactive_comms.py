"""These tests are to demonstrate how some expected behaviour between
an interactive node and a migen node with a FSM may fail due to a signal
being unavailable on specific clock cycles.
"""

import unittest

from migen import FSM, If, NextState, NextValue

from deltalanguage.data_types import (DInt,
                                      DOptional,
                                      make_forked_return)
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator
from deltalanguage.wiring import (DeltaGraph,
                                  Interactive,
                                  MigenNodeTemplate,
                                  PyInteractiveNode)


TestBenchForkT, TestBenchFork = make_forked_return(
    {
        'inp': int,
        'trigger': int
    }
)


@Interactive({}, TestBenchForkT)
def test_bench_no_trigger(node: PyInteractiveNode):
    """This node sends 2 consecutive messages, the first is a data signal, the
    second is a trigger to move out of a specific state of the migen FSM.
    """

    node.send(TestBenchFork(15, 0))
    node.send(TestBenchFork(0, 1))


@Interactive({}, TestBenchForkT)
def test_bench_yes_trigger(node: PyInteractiveNode):
    """This node sends 3 consecutive messages, the first is a data signal, the
    second is the same data signal, and the third is a trigger to move out of
    a specific state of the migen FSM.
    """

    node.send(TestBenchFork(15, 0))
    # make inp.data available for an extra cycle of migen clock
    node.send(TestBenchFork(15, 0))
    node.send(TestBenchFork(0, 1))


class TestMigenNode(MigenNodeTemplate):
    """A migen node that accepts a data signal, and a trigger signal that
    moves the FSM out of the "LOADING" state.
    """

    def migen_body(self, template):

        inp = template.add_pa_in_port('inp', DOptional(DInt()))
        trigger = template.add_pa_in_port('trigger', DOptional(DInt()))
        out = template.add_pa_out_port('out', DInt())

        # Declare input and output ports always happy to receive/transmit data
        self.comb += (
            inp.ready.eq(1),
            trigger.ready.eq(1),
            out.ready.eq(1),
        )

        commander_fsm = FSM(reset_state="IDLE")
        self.submodules.commander_fsm = commander_fsm

        commander_fsm.act(
            "IDLE",
            If(
                inp.valid == 1,
                NextState("LOADING")
            )
        )

        commander_fsm.act(
            "LOADING",
            If(
                trigger.valid & trigger.data == 1,
                NextState("RETURN")
            ).Else(
                NextValue(out.data, out.data + inp.data),
            )
        )

        commander_fsm.act(
            "RETURN",
            NextValue(out.valid, 1),
            NextState("IDLE")
        )


class MigenInteractiveCommsTest(unittest.TestCase):

    def setUp(self):

        self.saver = StateSaver(int)

    def test_migen_trigger_fails(self):
        """Assert that when the `test_bench_no_trigger` node sends data, the
        ouput of the migen node is 0 due to the data not loading into output
        signal properly.
        """

        with DeltaGraph() as graph:

            test_bench_output = test_bench_no_trigger.call()

            c1 = TestMigenNode(
                tb_num_iter=10
            ).call(
                inp=test_bench_output.inp,
                trigger=test_bench_output.trigger
            )

            self.saver.save_and_exit(c1.out)

        rt = DeltaPySimulator(graph)
        rt.run()

        self.assertEqual(self.saver.saved[0], 0)

    def test_migen_trigger_succeeds(self):
        """Assert that when the `test_bench_ye_trigger` node sends data, the
        ouput of the migen node is 15 since the data signal is available on the
        particular clock cycle that loads in the data.
        """

        with DeltaGraph() as graph:

            test_bench_output = test_bench_yes_trigger.call()

            c1 = TestMigenNode(
                tb_num_iter=10
            ).call(
                inp=test_bench_output.inp,
                trigger=test_bench_output.trigger
            )

            self.saver.save_and_exit(c1.out)

        rt = DeltaPySimulator(graph)
        rt.run()

        self.assertEqual(self.saver.saved[0], 15)


if __name__ == "__main__":
    unittest.main()
