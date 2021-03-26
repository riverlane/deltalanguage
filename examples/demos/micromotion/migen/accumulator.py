import matplotlib.pyplot as plt
from matplotlib import ticker
from progress.bar import Bar
import time
import math
import random
import numpy as np
import logging

import deltalanguage as dl

AccumT, AccumC = dl.make_forked_return({'DAC_command': int,
                                        'DAC_param': int,
                                        'photon': int,
                                        'reset': int})


TIME_RES = 30


@dl.Interactive([('new_time', dl.UInt()),
                 ('DAC_status', int),
                 ('DAC_voltage', int),
                 ('experiment_start', dl.Optional(bool))
                 ], AccumT)
def accumulator(node):
    """ Accumulator Node

    This node collects times sent from the counter FPGA node and issues
    commands to the DAC controller.

    This allows the node to collect data, fit to the data and feedback to the
    experiment. The process can loop until some minimum threshold is reached,
    allowing full automation of micromotion compensation.

    Inputs:
        - new_time: Time from Counter node
        - DAC_status: DAC status from DAC node
        - DAC_voltage: DAC voltage
        - experiment_start: Trigger from UI

    Outputs:
        - DAC_command: request to the DAC for it's status
        - DAC_param: new voltage for the DAC to be set to
        - photon: next photon detection time to simulate compensation
    """
    # DAC FSM states:
    STATUS = 0x01
    DAC_SET_VOLTAGE = 0x02
    DAC_GET_VOLTAGE = 0x03
    # DAC status
    READY = 0x00
    BUSY = 0x80

    # Internal constants
    EXP_LENGTH = 100  # How many photons do we want to collect
    V_REF = 5  # "ideal RF electrode voltage". arbitrary
    NB_STEPS = 5  # compensation iterations

    # Method to set the DAC voltage, check the DAC controller status
    # and confirm the new voltage. Once this method returns
    # we are ready to collect more data

    def dac_set(voltage):
        logging.basicConfig()

        print(f"Setting new voltage: {voltage}V")
        node.send(AccumC(DAC_command=DAC_SET_VOLTAGE,
                         DAC_param=voltage, photon=None, reset=0))
        # Poll the DAC controller while it's busy, this time it is setting the
        # voltage and waiting for it to settle.
        state = BUSY
        while state == BUSY:
            node.send(AccumC(DAC_command=STATUS,
                             DAC_param=None, photon=None, reset=None))
            state = node.receive('DAC_status')
            time.sleep(0.001)
        print("Voltage set")

        # Request the new voltage back from the DAC
        node.send(AccumC(DAC_command=DAC_GET_VOLTAGE,
                         DAC_param=None, photon=None, reset=None))
        volts = node.receive('DAC_voltage')
        print(f"New DAC voltage: {volts}V")

    full_histogram = []  # used for display over multiple iterations
    v_comp_list = []
    while True:
        v_comp = 0
        # Wait for an input from the UI
        if node.receive('experiment_start') is True:
            # Repeat the experiment for a range of compensation voltages

            for n in range(NB_STEPS):
                # dictionary for storing all the times received from counter.
                tau_range = [t for t in range(1, TIME_RES+1)]
                node.send(AccumC(DAC_command=None, DAC_param=None,
                                 photon=random.choice(tau_range), reset=1))
                # calculate the expected distribution
                limit = {t: math.trunc(EXP_LENGTH/(TIME_RES)
                                       * math.fabs(v_comp - V_REF)/V_REF
                                       * math.sin(2*math.pi/(TIME_RES)*t)
                                       + EXP_LENGTH/(TIME_RES))
                         + random.randint(-1, 1) for t in range(1, TIME_RES+1)}
                print(limit)
                histogram = {}
                prev_histogram = {}
                dac_set(v_comp)
                with Bar('Collecting photon data',
                         max=EXP_LENGTH,
                         suffix='%(percent)d%%') as bar:
                    while sum(histogram.values()) < sum(limit.values()):

                        # Wait here for an event
                        tau = node.receive('new_time')
                        if (tau is not None) and (tau != 0):

                            if tau in histogram:
                                histogram[tau] = histogram[tau] + 1
                            else:
                                histogram[tau] = 1

                            # range update
                            if (histogram[tau] >= limit[tau]):
                                if tau in tau_range:
                                    tau_range.remove(tau)
                            if tau_range:
                                photon = random.choice(tau_range)
                                node.send(
                                    AccumC(
                                        DAC_command=None,
                                        DAC_param=None,
                                        photon=photon,
                                        reset=1
                                    )
                                )
                                bar.next()

                # calculate compensation voltage
                if (prev_histogram):  # histogram not empty
                    if(max(histogram == EXP_LENGTH/(TIME_RES-1))):
                        v_comp = v_comp
                    elif (max(histogram) <= max(prev_histogram)):
                        v_comp += 1
                    else:
                        v_comp -= 1
                else:
                    v_comp += 1

                # histogram display
                histogram = histogram_maker(histogram)
                full_histogram.append(histogram)
                v_comp_list.append(v_comp-1)
            histogram_printer(full_histogram, v_comp_list)
            raise dl.DeltaRuntimeExit


def histogram_printer(data, voltage):
    print(data)
    plt.xlabel('Time between PMT and RF pulses (clock ticks)')
    plt.ylabel('Number of occurences')
    plt.title('Micromotion DEMO: Compensation of oscillation in ion-trap')
    plt.grid(b=True, which='major', color='#666666', linestyle='-', alpha=0.6)
    plt.minorticks_on()
    plt.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
    # lt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:d}'))
    for i in range(len(data)):
        print(i)
        plt.plot(list(data[i].keys()), data[i].values(),
                 color="ryckm"[i], label=f"{voltage[i]}V",
                 marker='o', linestyle='--')
    plt.legend()
    plt.savefig('histogram.png')

# add missing keys if any and sorts the histogram


def histogram_maker(data):
    for i in range(1, TIME_RES+1):
        if not (i in data):
            data[i] = 0
    return dict(sorted(data.items()))
