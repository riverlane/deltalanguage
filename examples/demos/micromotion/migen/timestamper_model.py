import logging
import random
import time

from migen import Array, If, Module, Signal

from deltalanguage.data_types import (DInt, DOptional,
                                      make_forked_return)
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import (DeltaGraph, Interactive, MigenNodeTemplate,
                                  PyInteractiveNode, placeholder_node_factory)


# globals
TEST_LENGTH = 2
TIME_RES = 32


class TimestamperModel(MigenNodeTemplate):
    """ This migen node is used as a simplified model of the
   ion-trap measurement system. It contains 2 main migen modules including:
        - a pulser simulating the RF and PMT trigger pulses
        - a timestamper modelling a high performance timestamper chip
        to measure the time interval between two pulses
    Inputs:
        - photon: photon detection event
        - reset: reset for the chip time reference counter
    Outputs:
        - time: the timestamp of a received trigger
    """

    class Pulser(Module):
        """ This migen module produces 2 single-clock-cycle pulses
        depending on a virtual photon detection event.
        PMT and RF triggers never occur at the same time.
        Inputs:
            - reset: signal
            - photon: signal
            - Time_res: parameter. maximum time interval between 2 triggers
        Outputs:
            - pmt_trigger: signal. photon detection trigger
            - rf_trigger: signal. electrode RF trigger
            - clock: signal. time reference
        """

        def __init__(self, reset, pmt_trigger, rf_trigger, photon, clock):

            # inputs
            self.reset = reset
            self.photon = photon

            # outputs
            self.pmt_trigger = pmt_trigger
            self.rf_trigger = rf_trigger
            self.clock = clock

            # internal signals
            self.photon_reg = Signal(5)

            ###

            self.sync += [
                If(
                    self.reset.data == 1,
                    self.clock.eq(0),
                ).Else(
                    self.clock.eq(self.clock + 1)
                ),
                If(
                    self.photon.valid,
                    self.photon_reg.eq(self.photon.data)
                ).Else(
                    self.photon_reg.eq(self.photon_reg)
                )
            ]

            self.comb += [
                If(
                    (self.clock == TIME_RES-1),
                    self.rf_trigger.eq(1),
                    self.pmt_trigger.eq(0)
                ).Elif(
                    (self.clock == TIME_RES-1 - self.photon_reg),
                    self.rf_trigger.eq(0),
                    self.pmt_trigger.eq(1)
                ).
                Else(
                    self.rf_trigger.eq(0),
                    self.pmt_trigger.eq(0)
                )
            ]

    class Timestamper(Module):
        """ This migen module is a simplified model of the HPTDC chip
        developed at CERN. It is capable of measuring the time of an event
        on any input channel using a counter as a reference.
        The real chip achieves sub-single-clock-cycle time resolution
        which is not reflected in this model.
        Inputs:
            - hit_channels: signal. parallel 1-bit-input channels
            - reset: signal. time reference reset
            - clock: signal. time reference
            - Time_res: parameter. maximum time interval between 2 triggers
        """
        NB_INPUTS = 2

        def __init__(self, hit_channels, time, reset, clock):

            # parameters

            # inputs
            self.hit_channels = hit_channels
            self.reset = reset
            self.clock = clock

            # outputs
            self.time = time

            # internal signals
            self.meta_reg1 = Signal(self.NB_INPUTS)
            self.meta_reg2 = Signal(self.NB_INPUTS)
            self.edge_reg = Signal(self.NB_INPUTS)
            self.edge_detect = Signal(self.NB_INPUTS)
            self.hit_time_regs = Array(Signal(TIME_RES)
                                       for a in range(self.NB_INPUTS))
            self.time_reg = Signal(TIME_RES)

            ####

            # edge detector with meta-stability removal register chain
            self.sync += [
                self.meta_reg1.eq(self.hit_channels),
                self.meta_reg2.eq(self.meta_reg1),
                self.edge_reg.eq(self.meta_reg2),
            ]

            for i in range(self.NB_INPUTS):
                self.sync += [
                    If(
                        self.edge_detect[i],  # pulse detected
                        self.hit_time_regs[i].eq(
                            self.clock)  # update hit register
                    ).Elif(
                        self.reset.data == 1,
                        self.hit_time_regs[i].eq(0),
                    ).Elif(
                        self.hit_time_regs[i] != 0,  # reset hit register
                        self.hit_time_regs[i].eq(0)
                    )
                ]

            self.comb += [
                self.time_reg.eq(self.hit_time_regs[0]
                                 | self.hit_time_regs[1])
            ]
            self.comb += [
                self.reset.ready.eq(1),
                self.time.data.eq(self.time_reg),
                self.edge_detect.eq(
                    ~self.edge_reg & self.meta_reg2),  # edge detection
                # output logic
                If(
                    self.time_reg != 0,
                    self.time.valid.eq(1)
                ).Else(
                    self.time.valid.eq(0)
                )
            ]

    def migen_body(self, template):
        """ This is the body of the migen node connecting
        the pulser and timestamper as 2 submodules.
        """

        # Node inputs
        self.reset = template.add_pa_in_port('reset', DOptional(DInt()))
        self.photon = template.add_pa_in_port('photon', DOptional(DInt()))

        # Node outputs
        self.time = template.add_pa_out_port('time', DInt())
        self.error = template.add_pa_out_port('error', DInt())

        self.rf_trigger = Signal(1)
        self.pmt_trigger = Signal(1)
        self.hit_channels = Signal(2)
        self.clock = Signal(TIME_RES)

        ###

        self.comb += [
            self.hit_channels.eq(self.pmt_trigger + 2*self.rf_trigger),
            self.photon.ready.eq(1),
        ]

        # error management ( if photon is outside valid range)
        self.sync += [
            If(
                self.photon.valid & ((self.photon.data < 1) | (
                    self.photon.data > TIME_RES-1)),
                self.error.data.eq(1),
                self.error.valid.eq(1)
            ).Elif(
                self.photon.valid,
                self.error.data.eq(0),
                self.error.valid.eq(1)
            ).Else(
                self.error.data.eq(self.error.data),
                self.error.valid.eq(0)
            )
        ]

        self.pulser_inst = TimestamperModel.Pulser(
            self.reset,
            self.pmt_trigger,
            self.rf_trigger,
            self.photon,
            self.clock
        )

        self.timestamper_inst = TimestamperModel.Timestamper(
            self.hit_channels,
            self.time,
            self.reset,
            self.clock
        )

        self.submodules += [self.timestamper_inst, self.pulser_inst]


TbT, TbC = make_forked_return({'reset': DInt(),
                               'photon': DInt()})


@Interactive({'time': DInt(), 'error': DInt()}, TbT)
def testbench(node: PyInteractiveNode):
    """ Testbench for Timestamper model node. Starts with random testing
    and ends with corner cases
    """

    for i in range(TEST_LENGTH):
        photon = random.randint(1, TIME_RES-2)
        do_test(i, photon, node)

    # corner cases
    # 1 : photon arrival time 0 - error expected
    do_test(-1, 0, node)
    # 2: photon arrival time TIME_RES - no expected error
    do_test(-2, TIME_RES-1, node)
    # 3: photon arrival time outside range - error expected
    do_test(-3, TIME_RES, node)

    raise DeltaRuntimeExit


def do_test(iteration, photon, node):
    # input register delay in timestamper
    delay_chain = 3
    node.send(TbC(reset=1, photon=photon))
    logging.debug(f'Testbench iter {iteration} [photon arrival time {photon}]')

    # compare expected vs actual time
    exp_time0 = TIME_RES - 2 - photon + delay_chain
    tb_time0 = node.receive('time')
    error = node.receive('error')

    logging.debug(f'expected time {exp_time0} --- real time {tb_time0}')
    logging.debug(f'error {error}')
    exp_time1 = TIME_RES - 2 + delay_chain
    if 0 < photon < TIME_RES:
        tb_time1 = node.receive('time')
        logging.debug(f'expected time {exp_time1} --- real time {tb_time1}')

    time.sleep(0.01)

    if 0 < photon < TIME_RES:
        assert tb_time0 == exp_time0
        assert tb_time1 == exp_time1
        assert error == 0
    else:
        assert error == 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    with DeltaGraph() as graph:

        # define placeholders
        p0_tb = placeholder_node_factory()

        dut = TimestamperModel(
            name="timestamper_model",
            vcd_name="tb_timestamper_model.vcd"
        ).call(
            reset=p0_tb.reset,
            photon=p0_tb.photon
        )

        tb = testbench.call(time=dut.time,
                            error=dut.error)

        # resolve placeholders
        p0_tb.specify_by_node(tb)

    # run graph
    print(graph)
    rt = DeltaPySimulator(graph)
    rt.run()
