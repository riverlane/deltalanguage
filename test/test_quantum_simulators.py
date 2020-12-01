import unittest

import numpy as np
from qiskit import execute, Aer
from projectq.backends import Simulator

from deltalanguage.lib.quantum_simulators import (ProjectqQuantumSimulator,
                                                  QiskitQuantumSimulator)
from deltalanguage.lib.hal import command_creator


class TestQuantumSimulators(unittest.TestCase):
    """
    Test that checks the equivalence of the projQ and Qiskit backend
    by running a simple test circuit and comparing if the final wavefunctions are equivalent
    (Ideally, one would compre the unitaries of the circuits instead.
    Can this be accessed in ProjectQ? )
    """

    def test_circuit_equivalence(self):

        # set the size of the register
        n_qubits = 3

        projQ_backend = ProjectqQuantumSimulator(register_size=n_qubits,
                                                 seed=234, backend=Simulator)
        qiskit_backend = QiskitQuantumSimulator(register_size=n_qubits,
                                                seed=234, simulator_backend=Aer.get_backend('statevector_simulator'))

        circuit = [
            ["STATE_PREPARATION", 0, 0],
            ['X', 0, 0],
            ['H', 0, 2],
            ["CONTROL", 0, 2],
            ["Y", 0, 1],
            ["T", 0, 0],
            ["SX", 0, 1],
            ["T", 0, 2],
            ["S", 0, 2],
            ["CONTROL", 0, 1],
            ["Z", 0, 2],
            ["T", 0, 2],
            ["INVS", 0, 2],
            ['RZ', 672, 1],
            ['SQRT_X', 0, 0],
            ["CONTROL", 0, 2],
            ["X", 0, 0],
            ["H", 0, 2],
            ["PIXY", 458, 1],
        ]

        for commands in circuit:

            hal_cmd = command_creator(*commands)

            projQ_backend.accept_command(hal_cmd)
            qiskit_backend.accept_command(hal_cmd)

        # compare wavefunction at the end of the circuit (before measuring)
        psi_projq = np.array(projQ_backend._engine.backend.cheat()[1])
        psi_qiskit = execute(qiskit_backend._circuit,
                             backend=qiskit_backend._simulator_backend).result().get_statevector(qiskit_backend._circuit)

        # send measure command to projQ backend (will complain if not flushed)
        projQ_backend.accept_command(command_creator(*['STATE_MEASURE', 0, 0]))

        # compare fidelities, i.e. are the final states equivalent?
        fidelity = np.abs(np.sum(psi_qiskit.conj() @ psi_projq))**2

        self.assertTrue(np.isclose(fidelity, 1.))


if __name__ == "__main__":
    unittest.main()
