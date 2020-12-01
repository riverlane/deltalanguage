import unittest

from qiskit import QuantumCircuit, execute, Aer
from qiskit.circuit.library import HGate, SGate

from deltalanguage.lib.hal import HardwareAbstractionLayerNode, command_creator
from deltalanguage.lib.quantum_simulators import (CustomNoiseModel,
                                                  QiskitQuantumSimulator)


""" 
Test file for the qiskit noise model with the following general idea:

- For each gate avaliable in the HAL backend, a circuit is constructed that 
implements the identity operation if and only if that gate has no errors.

- When errors are introduced for that gate, the circuit will be faulty, hence 
some measurements will not yield all zeros. 

Example circuits (h_perfect is a Hadamard without errors): 

    - Test of parametrised z-rotation RZ with angle Pi:
         ┌───────────┐┌────┐┌────┐┌───────────┐
    q_0: ┤ h_perfect ├┤ RZ ├┤ RZ ├┤ h_perfect ├
         └───────────┘└────┘└────┘└───────────┘

    - Test of X Gate:
         ┌───┐┌───┐
    q_0: ┤ X ├┤ X ├
         └───┘└───┘

    Test of CNOT gate:
         ┌───────────┐          ┌───────────┐
    q_0: ┤ h_perfect ├──■────■──┤ h_perfect ├
         └───────────┘┌─┴─┐┌─┴─┐└───────────┘
    q_1: ─────────────┤ X ├┤ X ├─────────────
                      └───┘└───┘             
"""


def run_gate_circuits(noise_model, gate_list, n_qubits):
    """Implements a test circuit for each gate in gate_list which is executed
    using the given noise_model

        Parameters
        ----------
        noise_model : NoiseModel    
            the noise model to apply to all test circuits 
        gate_list : List[string]
            list of HAL strings strings corresponding to one gate each
            these are the gates that will be checked for noise
        n_qubits : int
            number of qubits for the test circuit (1 or 2)

        Returns
        -------
        List[bool]
            for each test gate assigns true if there is noise on the test gate, 
            false if there is no noise, i.e. all zeros measured

        Raises
        ------
        ValueError
            No test circuit defined for a given gatestring in gate_list
    """

    # re-define gates with custom labels so that they are executed without noise
    H_perfect = HGate(label='h_perfect')
    S_perfect = SGate(label='s_perfect')

    circuit_errors = []  # list to append results to

    for gate in gate_list:

        q_sim = QiskitQuantumSimulator(register_size=n_qubits, seed=343,
                                       noise_model=noise_model)

        q_sim.accept_command(command_creator(*["STATE_PREPARATION", 0, 0]))

        if gate in ['H', 'RX', 'RY', 'SX', 'SY', 'X', 'Y']:
            q_sim.accept_command(command_creator(*[gate, 512, 0]))
            q_sim.accept_command(command_creator(*[gate, 512, 0]))

        elif gate in ['Z', 'R', 'RZ']:
            q_sim._circuit.append(H_perfect, [0])
            q_sim.accept_command(command_creator(*[gate, 512, 0]))
            q_sim.accept_command(command_creator(*[gate, 512, 0]))
            q_sim._circuit.append(H_perfect, [0])

        elif gate in ['PIZX']:
            q_sim._circuit.append(H_perfect, [0])
            q_sim.accept_command(command_creator(*[gate, 0, 0]))
            q_sim._circuit.append(S_perfect, [0])
            q_sim._circuit.append(S_perfect, [0])
            q_sim._circuit.append(H_perfect, [0])

        elif gate in ['PIYZ']:
            q_sim._circuit.append(H_perfect, [0])
            q_sim._circuit.append(S_perfect, [0])
            q_sim.accept_command(command_creator(*[gate, 0, 0]))
            q_sim._circuit.append(S_perfect, [0])
            q_sim._circuit.append(H_perfect, [0])

        elif gate in ['PIXY']:
            q_sim._circuit.append(H_perfect, [0])
            q_sim.accept_command(command_creator(*[gate, 0, 0]))
            q_sim._circuit.append(H_perfect, [0])

        elif gate in ['S', 'INVS']:
            q_sim._circuit.append(H_perfect, [0])
            for _ in range(4):
                q_sim.accept_command(command_creator(*[gate, 0, 0]))
            q_sim._circuit.append(H_perfect, [0])

        elif gate in ['SQRT_X']:
            for _ in range(4):
                q_sim.accept_command(command_creator(*[gate, 0, 0]))

        elif gate in ['T']:
            q_sim._circuit.append(H_perfect, [0])
            for _ in range(8):
                q_sim.accept_command(command_creator(*[gate, 0, 0]))
            q_sim._circuit.append(H_perfect, [0])

        elif gate in ['CX']:
            q_sim._circuit.append(H_perfect, [0])
            q_sim.accept_command(command_creator(*['CONTROL', 0, 0]))
            q_sim.accept_command(command_creator(*['X', 0, 1]))
            q_sim.accept_command(command_creator(*['CONTROL', 0, 0]))
            q_sim.accept_command(command_creator(*['X', 0, 1]))
            q_sim._circuit.append(H_perfect, [0])

        elif gate in ['CY']:
            q_sim._circuit.append(H_perfect, [0])
            q_sim.accept_command(command_creator(*['CONTROL', 0, 0]))
            q_sim.accept_command(command_creator(*['Y', 0, 1]))
            q_sim.accept_command(command_creator(*['CONTROL', 0, 0]))
            q_sim.accept_command(command_creator(*['Y', 0, 1]))
            q_sim._circuit.append(H_perfect, [0])

        elif gate in ['CZ']:
            q_sim._circuit.append(H_perfect, [0])
            q_sim._circuit.append(H_perfect, [1])
            q_sim.accept_command(command_creator(*['CONTROL', 0, 0]))
            q_sim.accept_command(command_creator(*['Z', 0, 1]))
            q_sim.accept_command(command_creator(*['CONTROL', 0, 0]))
            q_sim.accept_command(command_creator(*['Z', 0, 1]))
            q_sim._circuit.append(H_perfect, [0])
            q_sim._circuit.append(H_perfect, [1])

        else:
            raise ValueError('test circuit not defined for this gate')

        q_sim._circuit.measure_all()

        job = execute(q_sim._circuit, backend=q_sim._simulator_backend,
                      optimization_level=0,
                      basis_gates=q_sim._noise_model.basis_gates,
                      noise_model=q_sim._noise_model,
                      seed_simulator=243,
                      shots=100)

        result_dict = job.result().get_counts()

        if n_qubits == 1:
            if result_dict['0'] < 100:
                circuit_errors.append(True)
            else:
                circuit_errors.append(False)

        if n_qubits == 2:
            if result_dict['00'] < 100:
                circuit_errors.append(True)
            else:
                circuit_errors.append(False)

    return circuit_errors


class TestNoiseModel(unittest.TestCase):

    def setUp(self):
        """
        define the labels of the single and two-qubit gates to test
        """
        self.sq_gate_list = ['H', 'PIXY', 'PIYZ', 'PIZX', 'R', 'RX', 'RY', 'RZ',
                             'S', 'INVS', 'SQRT_X', 'SX', 'SY', 'T', 'X', 'Y',
                             'Z']

        self.tq_gate_list = ['CX', 'CY', 'CZ']

        # ideal noise model with all parameters set to zero
        self.ideal_noise_model = CustomNoiseModel(
            coherent_error_angles=[0, 0],
            depol_errors=[0, 0],
            damping_params=[0, 0, 0]
        )
        # list of all single-qubit noise types
        self.sq_noise_models = [
            CustomNoiseModel(coherent_error_angles=[0.3, 0.]),
            CustomNoiseModel(depol_errors=[0.3, 0.]),
            CustomNoiseModel(damping_params=[0.1, 0.1, 0.1]),
            CustomNoiseModel(relaxation_params=[0.1, 0.15, 0.1, 0.1])
        ]
        # list of all two-qubit noise types
        self.tq_noise_models = [
            CustomNoiseModel(coherent_error_angles=[0., 0.3]),
            CustomNoiseModel(depol_errors=[0., 0.3]),
        ]

    def test_circuits_without_error(self):
        """Check that for the ideal noise model, all circuits are indeed ideal
        and there are no errors
        """

        sq_errors = run_gate_circuits(self.ideal_noise_model,
                                      self.sq_gate_list, n_qubits=1)
        tq_errors = run_gate_circuits(self.ideal_noise_model,
                                      self.tq_gate_list, n_qubits=2)
        for outcome in (sq_errors + tq_errors):
            self.assertFalse(outcome)

    def test_single_qubit_errors(self):
        """Test that there are no errors on the single-qubit gates with the 
        two-qubit noise channels
        """
        for noise_type in self.tq_noise_models:
            for outcome in run_gate_circuits(noise_type, self.sq_gate_list, 1):
                self.assertFalse(outcome)

        """Test that there are errors on all single-qubit gates for all types 
        of single-qubit noise channels
        """
        for noise_type in self.sq_noise_models:
            for outcome in run_gate_circuits(noise_type, self.sq_gate_list, 1):
                self.assertTrue(outcome)

    def test_two_qubit_errors(self):

        for noise_type in self.sq_noise_models:
            for outcome in run_gate_circuits(noise_type, self.tq_gate_list, 2):
                self.assertFalse(outcome)

        for noise_type in self.tq_noise_models:
            for outcome in run_gate_circuits(noise_type, self.tq_gate_list, 2):
                self.assertTrue(outcome)


if __name__ == "__main__":
    unittest.main()
