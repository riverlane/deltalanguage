from migen import Signal, FSM, If, Memory, NextValue, NextState

import deltalanguage as dl

from examples.rabi_demo.helper_functions import generate_angles


ANGLE_MEMORY_WIDTH = 10  # argument length of HAL command
RESOLUTION = 4  # the total number of points is 2**RESOLUTION
REPETITIONS = 50  # number of shots for each point


class Aggregator(dl.MigenNodeTemplate):
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
        shot_completed = template.add_pa_in_port('shot_completed',
                                              dl.DOptional(dl.DBool()))
        hal_result = template.add_pa_in_port(
            'hal_result',
            dl.DOptional(dl.DUInt(dl.DSize(32)))
        )

        agg_result = template.add_pa_out_port('agg_result',
                                              dl.DInt(dl.DSize(32)))
        # Completed is currently returning a simple 0/1 value but we make space
        # for an error code to be returned e.g. 255, 0b11111111 can be in the
        # future used to represent an error.
        completed = template.add_pa_out_port('completed', dl.DInt(dl.DSize(8)))
        next_angle = template.add_pa_out_port(
            'next_angle',
            dl.DRaw(dl.DUInt(dl.DSize(ANGLE_MEMORY_WIDTH)))
        )

        # generate a ROM of 10-bit angle values
        angles = generate_angles(RESOLUTION)

        self.specials.angle_memory = angle_memory = Memory(
            ANGLE_MEMORY_WIDTH, len(angles), init=angles, name="ANGLE_ROM"
        )
        angle_rom_port = angle_memory.get_port(write_capable=False)
        self.specials += angle_rom_port

        # set up internal signals
        _shots_counter = Signal(32)
        _high_hal_results = Signal(32)
        _reset_high_hal = Signal(1)
        _angle_rom_index = Signal(RESOLUTION+1)

        self.comb += (
            # declare input/output ports always happy to receive/transmit data
            hal_result.ready.eq(1),
            shot_completed.ready.eq(1),

            # align angle ROM address with ROM index signal
            angle_rom_port.adr.eq(_angle_rom_index),
        )

        # define finite state machine for triggering angle and result signals
        self.submodules.rabi_aggregator_fsm = \
            rabi_aggregator_fsm = FSM(reset_state="IDLE")

        # Logic to accumulate measurements
        self.sync += (
            If (_reset_high_hal == 1,
                _high_hal_results.eq(0)
            ).Else (
                If (hal_result.valid == 1,
                    If ((hal_result.data &
                        dl.lib.Masks.MEASUREMENTS.value) == 1,
                        _high_hal_results.eq(_high_hal_results + 1)
                    )
                )
            )
        )

        # waits for the experiment to be kicked off

        rabi_aggregator_fsm.act(
            "IDLE",
            NextValue(agg_result.valid, 0),
            NextValue(next_angle.valid, 0),
            NextValue(completed.valid, 0),
            NextValue(_shots_counter, 0),
            NextValue(_reset_high_hal, 1),
            NextState("DO_SHOTS")
        )

        rabi_aggregator_fsm.act(
            "DO_SHOTS",
            NextValue(agg_result.valid, 0),
            NextValue(_reset_high_hal, 0),
            If (_shots_counter == REPETITIONS,
                NextState("CHECK_IF_COMPLETE"),
                NextValue(_angle_rom_index, _angle_rom_index + 1),
                NextValue(agg_result.data, _high_hal_results),
                NextValue(agg_result.valid, 1),
                NextValue(_reset_high_hal, 1),
             ).Else (
                NextValue(next_angle.data, angle_rom_port.dat_r),
                NextValue(next_angle.valid, 1),
                NextState("WAIT_SHOT")
            )
        )

        rabi_aggregator_fsm.act(
            "WAIT_SHOT",
            NextValue(next_angle.valid, 0),
            If ((shot_completed.valid == 1) & (shot_completed.data == 1),
                NextValue(_shots_counter, _shots_counter + 1),
                NextState("DO_SHOTS"),
            )
        )

        rabi_aggregator_fsm.act(
            "CHECK_IF_COMPLETE",
            NextState("IDLE"),
            NextValue(agg_result.valid, 0),
            If(_angle_rom_index == 2 ** RESOLUTION,
                NextValue(completed.data, 1),
                NextValue(completed.valid, 1),
            )
        )
