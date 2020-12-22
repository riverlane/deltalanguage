from abc import ABC, abstractclassmethod

from deltalanguage.data_types import DUInt, DSize


class IQuantumSimulator(ABC):
    """Abstract class for interfacing with a quantum simulators that interacts
    with the HAL.
    """

    @abstractclassmethod
    def accept_command(
        cls,
        command: DUInt(DSize(32))
    ) -> DUInt(DSize(32)):
        """Performs required logic based on received commands, and returns
        results if command is a measurement.

        Parameters
        ----------
        command : DInt(DSize(32))
            The HAL command to deconstruct and use to perform actions.

        Returns
        -------
        DInt(DSize(32))
            Result of a measurement command.


        .. TODO:: Isn't it supposed to be a ``DeltaMethodBlock``?
        """
        pass
