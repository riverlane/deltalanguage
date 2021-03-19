from migen import FSM, If, NextState, NextValue, Signal

import deltalanguage as dl

from examples.rabi_demo.aggregator import ANGLE_MEMORY_WIDTH


class Commander(dl.MigenNodeTemplate):
    """Migen node that contains a state machine to trigger HAL commands
    that execute a Rabi circuit by state preparation, qubit rotation (RX),
    and state measurement.

    Input signals:
    - angle: the representation of the rotation angle with a variable size

    Output signals:
    - hal_command: the 32-bit HAL command
    """

    def migen_body(self, template):
        # creation of input/output ports
        angle = template.add_pa_in_port(
            'angle',
            dl.DOptional(dl.DRaw(dl.DUInt(dl.DSize(ANGLE_MEMORY_WIDTH))))
        )

        hal_command = template.add_pa_out_port('hal_command',
                                               dl.DUInt(dl.DSize(32)))
        shot_completed = template.add_pa_out_port('shot_completed',
                                               dl.DBool())
        # set up  internal signals
        _rotation_command = Signal(32)

        self.comb += (
            # declare input/output ports always happy to receive/transmit data
            angle.ready.eq(1)
        )

        # define finite state machine for triggering HAL command sequences
        self.submodules.commander_fsm = \
            commander_fsm = FSM(reset_state="STATE_PREPARATION")

        # waits for angle signal before kicking off HAL sequence
        commander_fsm.act(
            "STATE_PREPARATION",
            NextValue(shot_completed.valid, 0),
            If(
                angle.valid == 1,
                NextValue(
                    _rotation_command,
                    dl.lib.command_creator("RX", argument=angle.data)
                ),
                NextValue(hal_command.valid, 1),
                NextValue(
                    hal_command.data,
                    dl.lib.command_creator("STATE_PREPARATION")
                ),
                NextState("ROTATION")
            ).Else(
                NextValue(hal_command.valid, 0),
                NextState("STATE_PREPARATION")
            )
        )

        # align HAL command to rotation
        commander_fsm.act(
            "ROTATION",
            NextValue(hal_command.valid, 1),
            NextValue(hal_command.data, _rotation_command),
            NextValue(shot_completed.valid, 0),
            NextState("STATE_MEASURE")
        )

        # align HAL command to state measure
        commander_fsm.act(
            "STATE_MEASURE",
            NextValue(hal_command.valid, 1),
            NextValue(hal_command.data,
                      dl.lib.command_creator("STATE_MEASURE")),
            NextValue(shot_completed.valid, 1),
            NextValue(shot_completed.data, 1),
            NextState("STATE_PREPARATION")
        )
