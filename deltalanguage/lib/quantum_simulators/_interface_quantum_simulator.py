from abc import ABC, abstractclassmethod

from deltalanguage.data_types import UInt, Size


class IQuantumSimulator(ABC):
    """Abstract class for interfacing with a quantum simulators that interacts
    with the HAL.
    """

    @abstractclassmethod
    def accept_command(
        cls,
        command: UInt(Size(32))
    ) -> UInt(Size(32)):
        """Performs required logic based on received commands, and returns
        results if command is a measurement.

        Parameters
        ----------
        command : UInt(Size(32))
            The HAL command to deconstruct and use to perform actions.

        Returns
        -------
        UInt(Size(32))
            Result of a measurement command.
        """
        pass
