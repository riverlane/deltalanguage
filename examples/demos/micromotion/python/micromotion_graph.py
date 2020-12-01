import matplotlib.pyplot as plt
from progress.bar import Bar
import random
import time

from deltalanguage.data_types import DOptional, make_forked_return
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  Interactive,
                                  PyInteractiveNode,
                                  placeholder_node_factory)


ExpT, ExpVal = make_forked_return({'pmt_trigger': bool, 'rf_trigger': bool})


@Interactive({}, ExpT)
def triggers(node: PyInteractiveNode):
    """ triggers
    This node simulates the two trigger pulses.
    The experiment measures a photon click on a PMT, then counts until the
    next RF trigger.
    This node generates these randomly spaced triggers.

    Since, the runtime runs each node seemingly randomly and there is no shared
    clock then the time between pulses and the time measured between pulses is
    junk.
    In this demo these two nodes need to be sync'd
    """

    sys_clk = 0
    photon = 0
    while True:
        sys_clk += 1

        if sys_clk == 100:
            node.send(ExpVal(pmt_trigger=False, rf_trigger=True))
            # The nodes are asynchronous, time is random even if fixed here
            photon = random.randrange(10, 99)
            sys_clk = 0

        elif photon == sys_clk:
            node.send(ExpVal(pmt_trigger=True, rf_trigger=False))

        else:
            node.send(ExpVal(pmt_trigger=False, rf_trigger=False))


@Interactive({'pmt': DOptional(bool), 'rf': DOptional(bool)}, int)
def counter(node: PyInteractiveNode):
    """ counter
    The counter node receives the 2 trigger pulses from hardware and counts the
    time between the pulses. The unit of time in a real system will be clock
    ticks from the fastest clock available!
    """

    while True:
        if node.receive('pmt') is True:
            start = time.time()  # record the time when the photon arrived
            while node.receive('rf') is not True:  # Hold until RF trigger
                pass

            # Calculate time between triggers
            cnt = (time.time() - start)
            node.send(cnt)


DACT, DACVals = make_forked_return(
    {'node_status': int, 'return_data': int, 'rx_data': int}
)


@Interactive({'command': DOptional(int), 'params': int}, DACT)
def DAC_control(node: PyInteractiveNode):
    """ DAC_control
    This node is the interface between our graph and the DAC hardware. rx_data
    would be linked to an SPI DAC, in this example is goes nowhere.

    This node is built as a finite state machine, the accumulator
    node can issue different commands to control the state machine.
    """
    # FSM state commands
    _STATUS = 0x01
    _DAC_SET_VOLTAGE = 0x02
    _DAC_GET_VOLTAGE = 0x03

    # Node Status'
    _READY = 0x01
    _BUSY = 0x80

    # local variables
    voltage = 10
    # In this python example the status doesn't currently have any use.
    # However, it becomes more relavent when we move to a migen implementation.
    # It could be used here to report back errors between the DAC and
    # DAC controller
    node_status = _READY

    # Finite state machine callback methods
    def dac_status_callback():
        print("dac_status_callback")
        nonlocal node_status
        node.send(DACVals(node_status=node_status,
                          return_data=None,
                          rx_data=None))

    def dac_set_voltage_callback():
        print("dac_set_voltage_callback")
        nonlocal voltage
        voltage = node.receive('params')
        # Send voltage to the SPI controller
        node.send(DACVals(node_status=None, return_data=None, rx_data=voltage))

    def dac_get_voltage_callback():
        print("dac_get_voltage_callback")
        nonlocal voltage
        node.send(DACVals(node_status=None, return_data=voltage, rx_data=None))

    # DAC finite state machine.
    switcher = {_STATUS: dac_status_callback,
                _DAC_SET_VOLTAGE: dac_set_voltage_callback,
                _DAC_GET_VOLTAGE: dac_get_voltage_callback
                }

    # Body of our node. Wait for incoming commands from the accumulator
    while True:
        # Non-block receive to allow for other processes in this while loop
        cmmd = node.receive('command')
        if cmmd is not None:
            switcher[cmmd]()  # If we have a command issue that to the FSM
        time.sleep(0.001)


AccumT, AccumVals = make_forked_return({'DAC_command': int,
                                        'DAC_param': int})


@Interactive({'new_time': int,
              'DAC_status': int,
              'DAC_voltage': int,
              'experiment_start': DOptional(bool)
              }, AccumT)
def accumulator(node: PyInteractiveNode):
    """ Accumulator Node

    This node both collects times reports from the counter FPGA node but also
    can issue commands to the DAC controller.

    This allows the node to collect data, fit to the data and feedback to the
    experiment. The process can loop until some minimum threshold is reached.
    Allowing full automation of micromotion compensation.

    Inputs:
    new_time: Time from Counter node
    DAC_status: DAC status from DAC node
    DAC_voltage: DAC voltage
    experiment_start: Trigger from UI

    Outputs:
    DAC_command: request to the DAC for it's status
    DAC_param: new voltage for the DAC to be set to
    """

    # DAC FSM states:
    _STATUS = 0x01
    _DAC_SET_VOLTAGE = 0x02
    _DAC_GET_VOLTAGE = 0x03
    # DAC status
    _READY = 0x00
    _BUSY = 0x80
    # Internal constants
    _EXP_LENGTH = 10  # How many photons do we want to collect

    # Method to set the DAC voltage, check the DAC controller status and
    # confirm the new voltage. Once this method returns we are ready
    # to collect more data
    def dac_set(voltage):
        print("Setting new voltage:", voltage, "v")
        node.send(AccumVals(DAC_command=_DAC_SET_VOLTAGE, DAC_param=voltage))
        # Poll the DAC controller while it's busy, this time it is setting the
        # voltage and waiting for it to settle.
        state = _BUSY
        while state == _BUSY:
            node.send(AccumVals(DAC_command=_STATUS, DAC_param=None))
            state = node.receive('DAC_status')
            time.sleep(0.001)
        print("Voltage set")

        # Request the new voltage back from the DAC
        node.send(AccumVals(DAC_command=_DAC_GET_VOLTAGE, DAC_param=None))
        volts = node.receive('DAC_voltage')
        print("New DAC voltage:", volts, "v")

    while True:
        compensation_v = 0
        # Wait for an input from the UI
        if node.receive('experiment_start') is True:
            # Repeat the experiment for a range of compensation voltages
            # In this demo the voltage doesn't affect the result
            for compensation_v in range(5):
                # dictionary for storing all the times recieved from counter.
                histogram = {}
                dac_set(compensation_v)

                with Bar('Collecting photon data',
                         max=_EXP_LENGTH,
                         suffix='%(percent)d%%') as bar:
                    while sum(histogram.values()) < _EXP_LENGTH:
                        # Wait here for an event
                        tau = node.receive('new_time')
                        if tau is not None:
                            if tau in histogram:
                                histogram[tau] = histogram[tau] + 1
                            else:
                                histogram[tau] = 1
                            bar.next()

            # Print a histogram of the collected data
            histogram_printer(histogram)
            raise DeltaRuntimeExit


def histogram_printer(data):
    print(data.values())
    plt.plot(list(data.keys()), data.values(), 'ro')
    plt.savefig('histogram.png')


@DeltaBlock()
def user_interface() -> bool:
    if input('Start Experiment (y/n): ') == 'y':
        return True
    else:
        raise DeltaRuntimeExit


with DeltaGraph() as graph:
    ui = user_interface()
    trig = triggers.call()
    cntr = counter.call(pmt=trig.pmt_trigger, rf=trig.rf_trigger)

    p1_dac_status = placeholder_node_factory()
    p2_dac_voltage = placeholder_node_factory()
    accume = accumulator.call(new_time=cntr,
                              DAC_status=p1_dac_status,
                              DAC_voltage=p2_dac_voltage,
                              experiment_start=ui)
    dac = DAC_control.call(command=accume.DAC_command, params=accume.DAC_param)
    p1_dac_status.specify_by_node(dac.node_status)
    p2_dac_voltage.specify_by_node(dac.return_data)

print(graph)
rt = DeltaPySimulator(graph)
rt.run()
