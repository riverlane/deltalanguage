import time
import logging

from migen import FSM, If, NextState, NextValue, Signal

import deltalanguage as dl


# Commands
DAC_STATUS = 0x01
DAC_SET_VOLTAGE = 0x02
DAC_GET_VOLTAGE = 0x03

# Status
BUSY = 0x80
READY = 0x00


class DACController(dl.MigenNodeTemplate):
    """ DAC controller should output instructions to DAC controlling ion
        trap electrodes. When a voltage update has been implemented wait for a
        settle time and initiate measurement of photon arrival times.

        Commands the DAC Controller accepts:
        - DAC Status - returns the current status of this node: Ready or Busy
        - DAC Set Voltage - Set the DAC to the voltage passed over param
        - DAC Get Voltage - Return the voltage the DAC is currently set to

        Node status can be requested at any time and is returned using a comb
        statement. The status is busy while handling requests or for a wait
        period after a new voltage is set.

        In real life this node would be connected over SPI to a real DAC.
        However, in this example all voltages are local variables.

    """

    def migen_body(self, template):
        # Node Inputs
        # Two inputs, a command and parameters.
        self.DAC_command = template.add_pa_in_port(
            'DAC_command', dl.DOptional(dl.DInt())
        )
        self.DAC_param = template.add_pa_in_port(
            'DAC_param', dl.DOptional(dl.DInt())
        )

        # Node Outputs
        # Returns the node status upon request
        self.DAC_controller_status = template.add_pa_out_port(
            'DAC_controller_status', dl.DInt()
        )
        # Data to be returned to accumulator eg DAC voltage
        self.DAC_return_data = template.add_pa_out_port(
            'DAC_return_data', dl.DInt()
        )

        # Internal signals.
        #####
        # How long to wait for the DAC voltage to settle after a new
        # voltage is set
        self.v_settle_count = Signal(10)
        # Tracks the current status of this node
        self.node_status_internal = Signal(8)
        # 10 bit voltage
        self.DAC_voltage = Signal(10)

        # If self.v_settle_count is not zero it means we've updated the voltage
        # and are waiting for it to settle before initiating more data
        # collection
        self.sync += If(
            self.v_settle_count != 0,
            self.v_settle_count.eq(self.v_settle_count - 1)
        )

        # If the DAC_command is a request of node status immediately return
        # present value of node status
        self.comb += If(
            self.DAC_command.data == DAC_STATUS,
            self.DAC_controller_status.data.eq(self.node_status_internal),
            self.DAC_controller_status.valid.eq(1)
        )

        """FSM
        The state machine is used to handle the different commands. These will
        likely involve further communication with the SPI drives to the DAC

        IDLE
        This is the default hold state. It stays here while there is nothing to
        do. When recieving a command the state is then changed appropriately.

        DAC_READ_VOLTAGE
        This state returns the current DAC voltage. This is stored locally in
        DAC_voltage, however, in a real implementation this state would read
        the voltage directly from the DAC IC and return this value.

        DAC_SET_VOLTAGE
        This state sets DAC_voltage equal to the value sent in DAC_param. In a
        real implementation this state would pass the correct set of SPI
        commands to set the DAC voltage.

        SETTLE_HOLD
        This state is used as a hold time after the DAC voltage is written. We
        can assume there is a none zero settle time for the new electrode
        voltage to be set and any oscillations to settle. The time in this hold
        state is set by the self.v_settle_count value, set when moving from
        DAC_SET_VOLTAGE. Once self.cnt reaches 0 then the FSM moves back to
        IDLE. While in this state a poll of the DAC_STATUS will return _BUSY
        """

        self.submodules.DAC_fsm = FSM(reset_state="IDLE")

        self.DAC_fsm.act(
            "IDLE",
            NextValue(self.DAC_command.ready, 1),
            NextValue(self.DAC_param.ready, 1),
            NextValue(self.DAC_return_data.valid, 0),
            If(
                self.DAC_command.data == DAC_GET_VOLTAGE,
                NextValue(self.node_status_internal, BUSY),
                NextState("DAC_READ_VOLTAGE")
            ).Elif(
                self.DAC_command.data == DAC_SET_VOLTAGE,
                NextValue(self.DAC_voltage, self.DAC_param.data),
                NextValue(self.node_status_internal, BUSY),
                NextState("DAC_SET_VOLTAGE")
            )
        )

        self.DAC_fsm.act(
            "DAC_READ_VOLTAGE",
            NextValue(self.DAC_return_data.data, self.DAC_voltage),
            NextValue(self.DAC_return_data.valid, 1),
            NextValue(self.node_status_internal, READY),
            NextState("IDLE")
        )

        self.DAC_fsm.act(
            "DAC_SET_VOLTAGE",
            NextValue(self.node_status_internal, BUSY),
            NextValue(self.v_settle_count, 0x1),
            NextState("SETTLE_HOLD")
        )

        self.DAC_fsm.act(
            "SETTLE_HOLD",
            If(
                self.v_settle_count == 0,
                NextValue(self.node_status_internal, READY),
                NextState("IDLE")
            )
        )


TbT, TbC = dl.make_forked_return({'cmd': dl.DInt(), 'param': dl.DInt()})


@dl.Interactive([('dac_status', dl.DInt()), ('dac_voltage', dl.DInt())], TbT)
def testbench(node):
    """ Testbench for the DAC controller node, coverage of all commands
    and parameters, out of range values, assertion of expected results
    """

    def do_send_cmd(node, cmd, param):
        # check if the module is READY
        if cmd != DAC_STATUS:
            while True:
                node.send(TbC(cmd=DAC_STATUS, param=None))
                status = node.receive('dac_status')
                if status == READY:
                    break
                    time.sleep(1e-6)

        node.send(TbC(cmd=cmd, param=param))

        if cmd == DAC_STATUS:
            status = node.receive('dac_status')
            return status
        elif cmd == DAC_GET_VOLTAGE:
            voltage = node.receive('dac_voltage')
            return voltage
        else:
            return -1

    # get status
    res = do_send_cmd(node, DAC_STATUS, None)
    assert(res == READY)
    logging.debug(f'result {res}, expected {READY}')

    # get voltage
    res = do_send_cmd(node, DAC_GET_VOLTAGE, None)
    assert(res == 0)
    logging.debug(f'result {res}, expected {0}')

    # get status
    res = do_send_cmd(node, DAC_STATUS, None)
    assert(res == READY)
    logging.debug(f'result {res}, expected {READY}')

    # set voltage
    res = do_send_cmd(node, DAC_SET_VOLTAGE, 5)
    assert(res == -1)
    logging.debug(f'result {res}, expected {-1}')

    # get status - wait for value to settle
    res = do_send_cmd(node, DAC_STATUS, None)
    assert(res == BUSY)
    logging.debug(f'result {res}, expected {BUSY}')

    # get voltage
    res = do_send_cmd(node, DAC_GET_VOLTAGE, None)
    assert(res == 5)
    logging.debug(f'result {res}, expected {5}')

    raise dl.DeltaRuntimeExit


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    with dl.DeltaGraph() as graph:

        # define placeholders
        p0_tb = dl.placeholder_node_factory()

        dut = DACController(
            name="dac_controller",
            vcd_name="tb_dac_controller.vcd"
        ).call(
            DAC_command=p0_tb.cmd,
            DAC_param=p0_tb.param
        )

        tb = testbench.call(dac_status=dut.DAC_controller_status,
                            dac_voltage=dut.DAC_return_data)

        # resolve placeholders
        p0_tb.specify_by_node(tb)

    # run graph
    print(graph)
    rt = dl.DeltaPySimulator(graph)
    rt.run()
