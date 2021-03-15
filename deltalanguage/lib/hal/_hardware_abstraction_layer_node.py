from deltalanguage.data_types import DUInt, DSize
from deltalanguage.wiring import DeltaMethodBlock, NodeTemplate

from ..quantum_simulators import IQuantumSimulator

hal_template = NodeTemplate(
    name="QSim",
    in_params={'hal_command': DUInt(DSize(32))},
    out_type=DUInt(DSize(32))
)

class HardwareAbstractionLayerNode:
    """Encapsulates a node which receives HAL commands and uses them to
    perform operations on a quantum device.

    Parameters
    ----------
    quantum_simulator : IQuantumSimulator
        Object with the IQuantumSimulator interface that accepts commands
        and returns measurement results.
    """

    def __init__(
        self,
        quantum_simulator: IQuantumSimulator
    ):
        self._quantum_simulator = quantum_simulator

    @DeltaMethodBlock(name="accept_command")
    def accept_command(self, hal_command: DUInt(DSize(32))) -> DUInt(DSize(32)):
        """Interface for ``quantum_simulator.accept_command`` that is used
        to create a graph node.

        Parameters
        ----------
        command : DUInt(DSize(32))
            The HAL command to deconstruct and use to perform actions.

        Returns
        -------
        DUInt(DSize(32))
            Result of a measurement command.
        """
        result = self._quantum_simulator.accept_command(hal_command)

        return result
