import time
import logging
import random
import math

from migen import If, Module, Signal, FSM, NextState, NextValue

import deltalanguage as dl

# testbench global
_TIME_RES = 32


class TimestampChipInterface(dl.MigenNodeTemplate):
    """This migen node is an interface to the high resolution (25 ps)
    time to digital converter.

    It reads out trigger-timestamp data via a data_ready / get_data
    handshake protocol from the chip and sends the relative time between
    a PMT and an RF trigger to the accumulator node.

    Inputs:
        - time_in: signal. time sent by the chip for an event
    Outputs:
        - time_out: signal. relative time between two events
        - reset: signal. reset time reference counters in chip model
    """

    def migen_body(self, template):

        _TIME_RES = 32
        # Node inputs
        self.time_in = template.add_pa_in_port('time_in', dl.DOptional(int))

        # Node outputs
        self.time_out = template.add_pa_out_port('time_out', dl.DInt())
        self.counter_reset = template.add_pa_out_port('counter_reset', dl.DInt())

        # Internal signals
        self.pmt_reg = Signal(_TIME_RES)
        self.rf_reg = Signal(_TIME_RES)
        self.pmt_trig = Signal(1)
        self.rf_trig = Signal(1)

        self.submodules.fsm = FSM(reset_state="RESET_COUNTER")

        self.sync += [
            If(
                self.pmt_trig,
                self.pmt_reg.eq(self.time_in.data),
            ).Elif(
                self.fsm.ongoing("RESET_COUNTER"),
                self.pmt_reg.eq(0)
            ).Else(
                self.pmt_reg.eq(self.pmt_reg)
            ),
            If(
                self.rf_trig,
                self.rf_reg.eq(self.time_in.data),
            ).Elif(
                self.fsm.ongoing("RESET_COUNTER"),
                self.rf_reg.eq(0)
            ).Else(
                self.rf_reg.eq(self.rf_reg)
            )
        ]

        """FSM
        The FSM is used to control the readouts from the HPTDC chip and
        generate a time signal for the accumulator

        RESET_COUNTER
        This is the dinitial state of the FSM at the start of the experiment.
        It resets the "coarse counter" of the HPTDC chip to establish a TO
        time reference.

        WAIT_FOR_PMT
        This state holds until the PMT timestamp is available at the HPTDC
        chip readout (first data_ready sync pulse)

        WAIT_FOR_RF
        This state holds until the RMT timestamp is available at the HPTDC
        chip readout (second data_ready sync pulse)

        SEND_TIME
        In this state, the difference between t_PMT and t_RF is derived and
        sent to the accumulator.

        WAIT_ACC_LATENCY
        This state is used to wait for any delays on inter-node communication
        """

        self.fsm.act(
            "RESET_COUNTER",
            self.pmt_trig.eq(0),
            self.rf_trig.eq(0),
            self.time_in.ready.eq(1),
            self.counter_reset.data.eq(1),  # reset counters
            self.counter_reset.valid.eq(1),
            NextState("WAIT_FOR_PMT")
        )

        self.fsm.act(
            "WAIT_FOR_PMT",
            self.counter_reset.data.eq(0),
            self.time_in.ready.eq(1),
            If(
                self.time_in.valid,
                self.pmt_trig.eq(1),
                NextState("WAIT_FOR_RF")
            )
        )

        self.fsm.act(
            "WAIT_FOR_RF",
            self.time_in.ready.eq(1),
            If(
                self.time_in.valid,
                self.rf_trig.eq(1),
                NextState("SEND_TIME")
            )
        )

        self.fsm.act(
            "SEND_TIME",
            self.time_in.ready.eq(1),
            self.time_out.data.eq(self.rf_reg - self.pmt_reg),
            self.time_out.valid.eq(1),
            NextState("WAIT_ACC_LATENCY")
        )

        self.fsm.act(
            "WAIT_ACC_LATENCY",
            If(
                self.time_in.valid == 0,
                NextState("RESET_COUNTER")
            )
        )


@dl.Interactive({'time_out': dl.DInt(), 'reset': dl.DInt()}, dl.DInt())
def testbench(node):
    """ Testbench for Timestamper interface node. Starts with random testing
    and ends with corner cases
    """
    _ITER = 10
    for i in range(_ITER):
        logging.debug(f'---Testbench iter {i}---')
        time_pmt = random.randint(0, 100)
        time_rf = random.randint(0, 100)
        do_test(node, time_pmt, time_rf)

    raise dl.DeltaRuntimeExit


def do_test(node, time_pmt, time_rf):
    logging.debug(f'PMT {time_pmt}, RF {time_rf}')
    reset = node.receive('reset')

    node.send(time_pmt)
    time.sleep(0.01)
    node.send(time_rf)
    time.sleep(0.01)
    time_out = node.receive('time_out')
    if time_rf >= time_pmt:
        exp_time = time_rf - time_pmt
    else:
        exp_time = math.pow(2, _TIME_RES) + time_rf - time_pmt
    logging.debug(
        f'time result {time_out}, expected time {exp_time}, reset {reset}')
    assert time_out == exp_time
    assert reset == 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    with dl.DeltaGraph() as graph:

        # define placeholders
        p0_tb = dl.placeholder_node_factory()

        dut = TimestampChipInterface(
            name="timestamper_interface",
            vcd_name="tb_timestamper_itf.vcd"
        ).call(
            time_in=p0_tb
        )

        tb = testbench.call(time_out=dut.time_out,
                            reset=dut.counter_reset)

        # resolve placeholders
        p0_tb.specify_by_node(tb)

    # run graph
    print(graph)
    rt = dl.DeltaPySimulator(graph)
    rt.run()
