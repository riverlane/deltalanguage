import subprocess
import unittest

from deltalanguage.lib.quantum_simulators import (ProjectqQuantumSimulator,
                                                  QiskitQuantumSimulator)
from deltalanguage.lib.hal import command_creator


class TestVirtualEmulator(unittest.TestCase):
    """Run integrated test."""

    def setUp(self):
        self.sim = ProjectqQuantumSimulator(register_size=2, seed=43)

    def test_register_size_error(self):
        with self.assertRaises(ValueError):
            cmd = command_creator("X", qubit=2)
            self.sim.accept_command(cmd)

    def test_too_many_controls_error(self):
        with self.assertRaises(ValueError):
            self.sim.accept_command(command_creator("STATE_PREPARATION"))
            self.sim.accept_command(command_creator("CONTROL", qubit=0))
            self.sim.accept_command(command_creator("CONTROL", qubit=1))

    def test_already_control_index_error(self):
        with self.assertRaises(ValueError):
            self.sim.accept_command(command_creator("STATE_PREPARATION"))
            self.sim.accept_command(command_creator("CONTROL", qubit=0))
            self.sim.accept_command(command_creator("CONTROL", qubit=0))

    def test_target_is_control_index_error(self):
        with self.assertRaises(ValueError):
            self.sim.accept_command(command_creator("STATE_PREPARATION"))
            self.sim.accept_command(command_creator("CONTROL", qubit=0))
            self.sim.accept_command(command_creator("RX", qubit=0))

    def test_result(self):
        pipes = subprocess.Popen(
            ['python', 'examples/virtual_emulator_python_qc/run_circuits.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        output, errors = pipes.communicate()
        output_val = float(output.decode("UTF-8").split(": ")[1])

        self.assertEqual(output_val, 0.1)
        self.assertEqual(errors, b'')


class TestQiskitBackend(unittest.TestCase):
    """Run integrated test."""

    def setUp(self):
        self.sim = QiskitQuantumSimulator(register_size=2, seed=137)

    def test_register_size_error(self):
        with self.assertRaises(ValueError):
            cmd = command_creator("X", qubit=2)
            self.sim.accept_command(cmd)

    def test_too_many_controls_error(self):
        with self.assertRaises(ValueError):
            self.sim.accept_command(command_creator("STATE_PREPARATION"))
            self.sim.accept_command(command_creator("CONTROL", qubit=0))
            self.sim.accept_command(command_creator("CONTROL", qubit=1))

    def test_already_control_index_error(self):
        with self.assertRaises(ValueError):
            self.sim.accept_command(command_creator("STATE_PREPARATION"))
            self.sim.accept_command(command_creator("CONTROL", qubit=0))
            self.sim.accept_command(command_creator("CONTROL", qubit=0))

    def test_target_is_control_index_error(self):
        with self.assertRaises(ValueError):
            self.sim.accept_command(command_creator("STATE_PREPARATION"))
            self.sim.accept_command(command_creator("CONTROL", qubit=0))
            self.sim.accept_command(command_creator("RX", qubit=0))

    def test_result(self):
        pipes = subprocess.Popen(
            ['python', 'examples/virtual_emulator_python_qc/qiskit_backend_circuit.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        output, errors = pipes.communicate()

        output_val = float(output.decode("UTF-8").split(": ")[1])

        self.assertEqual(output_val, 0.3)
        self.assertEqual(errors, b'')


if __name__ == "__main__":
    unittest.main()
