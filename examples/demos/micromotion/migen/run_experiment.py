import logging
import sys

import deltalanguage as dl

from accumulator import accumulator
from DAC_controller import DACController
from user_interface import user_interface
from timestamper_model import TimestamperModel
from timestamper_interface import TimestampChipInterface


if __name__ == "__main__":
    # Define Node debugging
    _DAC_DEBUG = logging.ERROR
    _COUNTER_DEBUG = logging.ERROR
    _TIMESTAMPER_DEBUG = logging.ERROR
    _CHIP_INTERFACE_DEBUG = logging.ERROR

    with dl.DeltaGraph() as graph:
        # UI acts as an experiment controller, this could be a GUI interface.
        UI = user_interface()

        # Place holders are required because of loops between
        # the DAC_controller, accumulator, timestamper and chip interface.
        p0_acc = dl.placeholder_node_factory()

        # DAC controller receives commands and parameters from accumulator.
        # This node could be used to control a DAC IC
        dac_node = DACController(
            'DAC_Control', lvl=_DAC_DEBUG
        ).call(
            DAC_command=p0_acc.DAC_command,
            DAC_param=p0_acc.DAC_param
        )

        # Timestamper model
        model_node = TimestamperModel(
            name='model',
            vcd_name='/workdir/model.vcd'
        ).call(
            reset=p0_acc.reset,
            photon=p0_acc.photon
        )

        # Timestamper interface
        interface_node = TimestampChipInterface(
            name='interface',
            vcd_name='/workdir/chip_interface.vcd'
        ).call(
            time_in=model_node.time
        )

        # Accumulator collects the times and generates a histogram.
        # It also issues commands to the DAC controller. Sends a new photon time
        # to the pulser according to expected distribution
        acc_node = accumulator.call(new_time=interface_node.time_out,
                                    DAC_status=dac_node.DAC_controller_status,
                                    DAC_voltage=dac_node.DAC_return_data,
                                    experiment_start=UI)

        # Fill in the placeholders used above
        p0_acc.specify_by_node(acc_node)

    # Run the graph until it reaches a natural exit
    # This happens after sufficient data has been collected.
    print(graph)
    rt = dl.DeltaPySimulator(graph)
    rt.run()
