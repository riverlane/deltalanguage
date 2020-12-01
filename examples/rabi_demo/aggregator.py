from migen import Signal, FSM, If, Memory, NextValue, NextState

from deltalanguage.data_types import DBool, DInt, DOptional, DSize
from deltalanguage.lib.hal import Masks
from deltalanguage.wiring import MigenNodeTemplate

from examples.rabi_demo.helper_functions import generate_angles


ANGLE_MEMORY_WIDTH = 10  # argument length of HAL command
RESOLUTION = 4  # the total number of points is 2**RESOLUTION
REPETITIONS = 50  # number of shots for each point


class Aggregator(MigenNodeTemplate):
    """Migen node that contains a state machine to trigger signals that output

    Input signals:
    - hal_result: signal representing result from the HAL

    Output signals:
    - agg_result: signal that stores aggregation of HAL results
    - completed: signal to flag when the whole process is finished
    - next_angle: the representation of the rotation angle with a variable size
    """

    def migen_body(self, template):
        # creation of input/output ports
        hal_result = template.add_pa_in_port(
            'hal_result',
            DOptional(DInt(DSize(32)))
        )

        agg_result = template.add_pa_out_port('agg_result', DInt(DSize(32)))
        # Completed is currently returning a simple 0/1 value but we make space
        # for an error code to be returned e.g. 255, 0b11111111 can be in the
        # future used to represent an error.
        completed = template.add_pa_out_port('completed', DInt(DSize(8)))
        next_angle = template.add_pa_out_port(
            'next_angle',
            DInt(DSize(ANGLE_MEMORY_WIDTH))
        )

        # generate a ROM of 10-bit angle values
        angles = generate_angles(RESOLUTION)

        self.specials.angle_memory = angle_memory = Memory(
            ANGLE_MEMORY_WIDTH, len(angles), init=angles, name="ANGLE_ROM"
        )
        angle_rom_port = angle_memory.get_port(write_capable=False)
        self.specials += angle_rom_port

        # set up internal signals
        _aggregation_counter = Signal(32)
        _high_hal_results = Signal(32)

        _angle_rom_index = Signal(RESOLUTION)
        _final_angle = Signal(1)

        self.comb += (
            # declare input/output ports always happy to receive/transmit data
            hal_result.ready.eq(1),

            # align angle ROM address with ROM index signal
            angle_rom_port.adr.eq(_angle_rom_index),
        )

        # define finite state machine for triggering angle and result signals
        self.submodules.rabi_aggregator_fsm = \
            rabi_aggregator_fsm = FSM(reset_state="IDLE")

        # waits for the experiment to be kicked off
        rabi_aggregator_fsm.act(
            "IDLE",
            NextState("RESULT_AGGREGATION")
        )

        # main state for orchestrating inputs/outputs
        # inputs: hal results
        # outputs: rotation angles, aggrgated results, completion flag
        rabi_aggregator_fsm.act(
            "RESULT_AGGREGATION",
            If(
                completed.data == 1,
                NextValue(agg_result.valid, 0),
                NextValue(completed.valid, 1),
                NextState("COMPLETED")

            ).Else(
                If(  # flag that we are on the final angle
                    _angle_rom_index == (2 ** RESOLUTION) - 1,
                    NextValue(_final_angle, 1)
                ),

                If(  # have gathered enough statistics
                    _aggregation_counter == REPETITIONS,

                    # make aggregation result available on output signal
                    NextValue(agg_result.valid, 1),

                    # reset internal hal result counter
                    NextValue(_high_hal_results, 0),

                    # move to next angle
                    NextValue(_angle_rom_index, _angle_rom_index + 1),

                    # reset aggregation counter
                    NextValue(_aggregation_counter, 0),

                    If(  # begin experiment shutdown, no error so sending a 1
                        _final_angle,
                        NextValue(completed.data, 1),
                        NextValue(next_angle.valid, 0)
                    )

                ).Else(  # waits here for a valid result from the HAL
                    If(
                        hal_result.valid,
                        NextValue(
                            _aggregation_counter,
                            _aggregation_counter + 1
                        ),
                        If(  # we only increment when the HAL result is 1
                            (hal_result.data & Masks.MEASUREMENTS.value) == 1,
                            NextValue(
                                _high_hal_results,
                                _high_hal_results + 1
                            )
                        )
                    ),

                    # align internal hal result counter with aggregation
                    NextValue(agg_result.data, _high_hal_results),

                    # align angle signal with current ROM address data
                    NextValue(next_angle.data, angle_rom_port.dat_r),

                    # ensure appropriate output signals are available
                    NextValue(agg_result.valid, 0),
                    NextValue(next_angle.valid, 1),
                )
            )
        )

        # experiment is completed, so reset all signals to idle state
        rabi_aggregator_fsm.act(
            "COMPLETED",
            NextValue(agg_result.valid, 0),
            NextValue(next_angle.valid, 0),
            NextValue(completed.data, 0),
            NextValue(completed.valid, 0),
            NextValue(_angle_rom_index, 0),
            NextState("IDLE")
        )
