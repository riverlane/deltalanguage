import warnings

import numpy as np

from qiskit import Aer, execute, QuantumCircuit
from qiskit.circuit.library import (HGate, SdgGate, SGate, TGate,
                                    XGate, YGate, ZGate)
from qiskit.extensions.unitary import UnitaryGate
from qiskit.providers.aer.noise import NoiseModel

from deltalanguage.data_types import DUInt, DSize

from . import IQuantumSimulator
from ..hal import Masks, Opcode, Shifts


# defining some custom gates that arise from twirling

class SxGate(UnitaryGate):
    def __init__(self):
        super().__init__(np.array([[0, 1], [1j, 0]]), label='SX')


class SyGate(UnitaryGate):
    def __init__(self):
        super().__init__(np.array([[0, 1j], [1, 0]]), label='SY')


class PiXY(UnitaryGate):
    """Pi-rotation with axis in x-y-plane gate class."""

    def __init__(self, angle):
        super().__init__(np.array([[0, -np.sin(angle) - 1j*np.cos(angle)],
                                   [np.sin(angle) - 1j*np.cos(angle), 0]]), label='PiXY')


class PiYZ(UnitaryGate):
    """Pi-rotation with axis in y-z-plane gate class."""

    def __init__(self, angle):
        super().__init__(np.array([[np.cos(angle), -1j*np.sin(angle)],
                                   [1j*np.sin(angle), -1*np.cos(angle)]]), label='PiYZ')


class PiZX(UnitaryGate):
    """Pi-rotation with axis in z-x-plane gate class."""

    def __init__(self, angle):
        super().__init__(np.array([[np.cos(angle), np.sin(angle)],
                                   [np.sin(angle), -1*np.cos(angle)]]), label='PiZX')


class RX(UnitaryGate):
    """ rotation around x-axis with custom label for noise model"""

    def __init__(self, angle):
        super().__init__(np.array([[1j*np.cos(angle/2), np.sin(angle/2)],
                                   [np.sin(angle/2), 1j*np.cos(angle/2)]]), label='RX')

# Some gates that already exist in qiskit need to redefined with a custom label
# so that they can be recognized by the noise model


class X(UnitaryGate):
    """ rotation around x-axis with custom label for noise model"""

    def __init__(self):
        super().__init__((np.array([[0, 1], [1, 0]]) + 0j), label='X')


class RY(UnitaryGate):
    """ rotation around y-axis with custom label for noise model"""

    def __init__(self, angle):
        super().__init__(np.array([[1j*np.cos(angle/2), -1j*np.sin(angle/2)],
                                   [1j*np.sin(angle/2), 1j*np.cos(angle/2)]]), label='RY')


class Y(UnitaryGate):
    """ rotation around x-axis with custom label for noise model"""

    def __init__(self):
        super().__init__(np.array([[0, -1j], [1j, 0]]), label='Y')


class RZ(UnitaryGate):
    """ rotation around z-axis with custom label for noise model"""

    def __init__(self, angle):
        super().__init__(1j*np.array([[np.exp(-1j*angle/2), 0],
                                      [0, np.exp(1j*angle/2)]]), label='RZ')


class Z(UnitaryGate):
    """ rotation around x-axis with custom label for noise model"""

    def __init__(self):
        super().__init__((np.array([[1, 0], [0, -1]]) + 0j), label='Z')


class SqrtXGate(UnitaryGate):
    def __init__(self):
        super().__init__(
            np.array([[1j, 1], [1, 1j]])/np.sqrt(2), label='sqrt_x')


class QiskitQuantumSimulator(IQuantumSimulator):
    """Qiskit implementation of the IQuantumSimulator interface.

    Parameters
    ----------
    register_size: int
        Size of the qubit register.
    seed : int
        seed for both the random transpiler and the measurement sampling
    simulator:
        specifies which qiskit simulator backend to use, possibilities are:
        QasmSimulator (default),
        StatevectorSimulator/UnitarySimulator (for debugging)


    .. TODO::
        Add and example how to use it in a graph (without any runtime).
        """

    def __init__(self,
                 register_size: int = 16,
                 seed: int = None,
                 simulator_backend=Aer.get_backend('qasm_simulator'),
                 noise_model=None
                 ):
        """Constructor.

        Parameters
        ----------
        register_size : int
            Size of the qubit register.
        seed : int
            seed for both the random transpiler and the measurement sampling
        simulator : AerBackend
            specifies which qiskit simulator backend to use, possibilities are:
            QasmSimulator, StatevectorSimulator/UnitarySimulator (for debugging)
        noise_model : NoiseModel
            the qiskit NoiseModel object to apply when running a circuit
        """

        self._circuit = None
        self._simulator_backend = simulator_backend
        np.random.seed(seed)
        self._seed = seed

        # defaulted to 16 because the bitcode status return
        # has 16 bits assigned for measurement results.
        self._qubit_register_size = register_size

        # stores control qubits
        self._control_qubit_indices = []

        # assign projectq gate to each opcode
        self._parameterised_gate_dict = {
            Opcode['R'].value: RZ,
            Opcode['RX'].value: RX,
            Opcode['RY'].value: RY,
            Opcode['RZ'].value: RZ,
            Opcode['PIXY'].value: PiXY,
            Opcode['PIYZ'].value: PiYZ,
            Opcode['PIZX'].value: PiZX,
        }

        self._constant_gate_dict = {
            Opcode['H'].value: HGate,
            Opcode['S'].value: SGate,
            Opcode['SQRT_X'].value: SqrtXGate,
            Opcode['T'].value: TGate,
            Opcode['X'].value: X,
            Opcode['Y'].value: Y,
            Opcode['Z'].value: Z,
            Opcode['INVS'].value: SdgGate,
            # consecutive S and X gate needed for RC
            Opcode['SX'].value: SxGate,
            # consecutive S and Y gate needed for RC
            Opcode['SY'].value: SyGate,
        }

        if noise_model is not None:
            assert isinstance(noise_model, NoiseModel)
            self._noise_model = noise_model
        else:
            self._noise_model = NoiseModel()

    def apply_gate(self, gate, qubit_index: int, parameter: float = None):
        """Receives command information and implements the gate on the
        corresponding qubit.

        Parameters
        ----------
        gate : UnitaryGate
            Qiskit gate to be applied.
        qubit_index : int
            Index of qubit for gate to be applied to.
        parameter : float
            Angle of gate if parametrised.
        """
        if self._circuit is not None:

            if len(self._control_qubit_indices) == 0:  # single qubit gate

                if parameter is not None:
                    self._circuit.append(gate(parameter), [qubit_index])
                else:
                    self._circuit.append(gate(), [qubit_index])

            else:  # controlled gate

                if qubit_index in self._control_qubit_indices:
                    raise ValueError(
                        f"Target qubit {qubit_index} already set-up as " +
                        "control qubit!"
                    )

                control_number = len(self._control_qubit_indices)

                if gate == X:
                    gate = XGate
                elif gate == Y:
                    gate = YGate
                elif gate == Z:
                    gate = ZGate
                else:
                    warnings.warn("Noise not supported on cotrolled gates " +
                                  "besides CX, CY and CZ")

                gate_indices = self._control_qubit_indices + [qubit_index]

                if parameter is not None:
                    controlled_gate = gate(parameter).control(control_number)
                else:
                    controlled_gate = gate().control(control_number)

                self._circuit.append(controlled_gate, gate_indices)

                # reset control indices
                self._control_qubit_indices = []

    def accept_command(
        self,
        command: DUInt(DSize(32))
    ) -> DUInt(DSize(32)):

        op = command >> Shifts.OPCODE.value
        qubit_index = (command & Masks.QUBIT_INDEX.value)

        if qubit_index + 1 > self._qubit_register_size:
            raise ValueError(
                f"Qubit index ({qubit_index}) greater than " +
                f"register size ({self._qubit_register_size})!"
            )

        if op == Opcode["STATE_PREPARATION"].value:
            self._circuit = None

            self._circuit = QuantumCircuit(self._qubit_register_size)

        elif op == Opcode["STATE_MEASURE"].value:

            self._circuit.measure_all()

            job = execute(self._circuit, backend=self._simulator_backend,
                          optimization_level=0,
                          basis_gates=self._noise_model.basis_gates,
                          noise_model=self._noise_model,
                          seed_simulator=np.random.randint(self._seed), shots=1)

            result_dict = job.result().get_counts()

            outcome_string = list(result_dict.keys())[0]

            # Each measurement sent should have all valid flags.
            # Therefore valid mask added to the 16bit measurement bitcode.
            measurement_binary = Masks.VALIDS.value
            # convert binary string to int,
            # qubit index 0 is least significant bit in the binary expansion
            measurement_binary += int(outcome_string, 2)

            return measurement_binary

        elif op == Opcode["CONTROL"].value:

            # add qubit index to self.control_qubit_indices, store
            # in memory until a gate is called, which is run controlled
            # on these qubits.

            if qubit_index in self._control_qubit_indices:
                raise ValueError(
                    f"Qubit {qubit_index} already set-up as control qubit!"
                )

            if len(self._control_qubit_indices)+1 == self._qubit_register_size:

                raise ValueError(
                    "Too many control qubits for register size of " +
                    "f{self._qubit_register_size}!"
                )

            self._control_qubit_indices += [qubit_index]

        elif op in self._parameterised_gate_dict.keys():
            angle = (command & Masks.ARG.value) >> Shifts.ARG.value
            angle *= (2 * np.pi) / 1024
            gate = self._parameterised_gate_dict[op]

            self.apply_gate(gate, qubit_index, angle)

        elif op in self._constant_gate_dict.keys():
            gate = self._constant_gate_dict[op]
            self.apply_gate(gate, qubit_index)

        elif op == Opcode['ID'].value:
            pass

        else:
            raise TypeError(f"{op} is not a recognised opcode!")
