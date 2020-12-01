
from typing import List

import numpy as np
from qiskit.providers.aer.noise import (
    coherent_unitary_error,
    depolarizing_error,
    NoiseModel,
    phase_amplitude_damping_error,
    thermal_relaxation_error
)


class CustomNoiseModel(NoiseModel):
    """
    Class that inherits from Qiskit's NoiseModel class for easy contruction of
    noise models suited to the gateset currently defined in the HAL.
    """

    def __init__(self,
                 coherent_error_angles: List[float] = None,
                 depol_errors: List[float] = None,
                 damping_params: List[float] = None,
                 relaxation_params: List[float] = None,
                 ):
        """Creating the noise model object and specifying the used gateset All
        erros are assigend uniformly to the set of single-/two-qubit gates

            Parameters
            ----------
            coherent_error_angles : List[float], optional
                angles of unitary over-rotaions for single, and two-qubit gates,
                by default None
            depol_errors : List[float], optional
                params of single- and two-qubit depolarization noise channels,
                by default None
            damping_params : List[float], optional
                amplitude damping, phase damping and excited state population
                of a general amplitude + phase damping channel, by default None
            relaxation_params : List[float], optional
                t1 time, t2 time, timestep (unit of time) and excited state
                population of a thermal relaxation noise channel,
                by default None
            """

        # create "empty" noise model from the original Qiskit class
        # Need to specify the basis of all qiskit prebuilt gates that should be
        # noisy
        super().__init__(basis_gates=['h', 't', 'x', 'y', 's', 'sdg', 'z',
                                      'cx', 'cy', 'cz'])

        # list of qiskit labels of all single qubit gates specified in the HAL
        # For all single qubit gates defined used in the Qiskit HAL, the
        # corresponding label must be given here, so that errors are assigned
        # to that gate
        # Uppercase letters are custom gates defined in the Qiskit backend
        # while lowercase labels are default qiskit labels
        self._sq_gates = ['h', 'PiXY', 'PiYZ', 'PiZX', 'R', 'RX', 'RY', 'RZ',
                          's', 'sdg', 'sqrt_x', 'SX', 'SY', 't', 'X', 'Y', 'Z']
        # list of qiskit labels of all two qubit gates specified in the HAL
        self._tq_gates = ['cx', 'cy', 'cz']

        # defining matrix representations of Pauli gates
        self.gate2matrix_dict = {
            'X': np.array([[0, 1], [1, 0]]) + 0j,
            'Y': np.array([[0, -1j], [1j, 0]]),
            'Z': np.array([[1, 0], [0, -1]]) + 0j,
        }

        # adding coherent overrotations to each single and two-qubit gate
        # using Qiskit's unitary error. This will be applied every time the
        # original gate is executed in a circuit
        if coherent_error_angles is not None:

            assert isinstance(coherent_error_angles, list), \
                'Need list of Single-qubit and two-qubit gate errors'
            assert len(coherent_error_angles) == 2

            self.sq_angle, self.tq_angle = coherent_error_angles

            error_h = coherent_unitary_error(
                self._sq_rot(self.sq_angle, np.pi/4, 0))
            self.add_all_qubit_quantum_error(error_h, ['h'])

            error_x = coherent_unitary_error(
                self._sq_rot(self.sq_angle, np.pi/2, 0))
            self.add_all_qubit_quantum_error(error_x, ['X', 'RX', 'PiYZ',
                                                       'sqrt_x'])

            error_y = coherent_unitary_error(
                self._sq_rot(self.sq_angle, np.pi/2, np.pi/2))
            self.add_all_qubit_quantum_error(error_y, ['Y', 'RY', 'PiZX'])

            error_z = coherent_unitary_error(self._sq_rot(self.sq_angle, 0, 0))
            self.add_all_qubit_quantum_error(error_z,
                                             ['Z', 'RZ', 's', 'sdg', 't', 'PiXY'])

            error_sx = coherent_unitary_error(
                self._sq_rot(self.sq_angle, np.pi/2, np.pi/4))
            self.add_all_qubit_quantum_error(error_sx, ['SX'])

            error_sy = coherent_unitary_error(
                self._sq_rot(self.sq_angle, np.pi/2, -np.pi/4))
            self.add_all_qubit_quantum_error(error_sy, ['SY'])

            error_cx = coherent_unitary_error(
                self._contr_sq_rot(self.tq_angle, np.pi/2, 0))
            self.add_all_qubit_quantum_error(error_cx, ['cx'])

            error_cy = coherent_unitary_error(
                self._contr_sq_rot(self.tq_angle, np.pi/2, np.pi/2))
            self.add_all_qubit_quantum_error(error_cy, ['cy'])

            error_cz = coherent_unitary_error(
                self._contr_sq_rot(self.tq_angle, 0, 0))
            self.add_all_qubit_quantum_error(error_cz, ['cz'])

        # adding a depolarization channel
        if depol_errors is not None:

            assert isinstance(depol_errors, list), \
                'Need list of Single-qubit and two-qubit depolarization params'
            assert len(depol_errors) == 2

            self.sq_depol, self.tq_depol = depol_errors

            sq_depol_error = depolarizing_error(self.sq_depol, 1)
            self.add_all_qubit_quantum_error(
                sq_depol_error, self._sq_gates, warnings=False)

            tq_depol_error = depolarizing_error(self.tq_depol, 2)
            self.add_all_qubit_quantum_error(
                tq_depol_error, self._tq_gates, warnings=False)

        # adding an amplitude and/or phase damping channel
        if damping_params is not None:

            assert isinstance(damping_params, list), \
                'Need list of amplitude damping, phase damping and excited \
                     state population'
            assert len(damping_params) == 3

            self.amp_param, self.phase_param, self.amp_pop = damping_params

            damping_error = phase_amplitude_damping_error(self.amp_param,
                                                          self.phase_param,
                                                          self.amp_pop)
            self.add_all_qubit_quantum_error(
                damping_error, self._sq_gates, warnings=False)

        # adding a themral relaxation error
        if relaxation_params is not None:

            assert isinstance(relaxation_params, list), \
                'Need list of t1 time, t2 time, gate time and ex. state pop.'
            assert len(relaxation_params) == 4

            self.t1, self.t2, self.time, self.damp_pop = relaxation_params

            relaxation_error = thermal_relaxation_error(self.t1,
                                                        self.t2,
                                                        self.time,
                                                        self.damp_pop)
            self.add_all_qubit_quantum_error(
                relaxation_error, self._sq_gates, warnings=False)

        # add the 'unitary' label to the basis set for all the custom gates
        # in the HAL specified as a UnitaryGate object
        self.add_basis_gates(['unitary'])

    def _sq_rot(self, lamda, theta, phi):
        """build the matrix form of a single qubit rotation of angle lamda
           with direction set by theta, phi in spherical coord.

            Parameters
            ----------
            lamda : float
                rotation angle
            theta : float
                azimuthal angle of the rotation axis
            phi : float
                polar angle of the rotation axis

            Returns
            -------
            np.array[float]
                2x2 array of the single qubit rotation gate
        """

        unitary = np.cos(lamda/2)*np.eye(2) + 0j
        unitary += -1j*np.sin(lamda/2)*np.sin(theta)*np.cos(phi) \
            * (np.array([[0, 1], [1, 0]]) + 0j)
        unitary += -1j*np.sin(lamda/2)*np.sin(theta)*np.sin(phi) \
            * np.array([[0, -1j], [1j, 0]])
        unitary += -1j*np.sin(lamda/2)*np.cos(theta) *\
                                             (np.array([[1, 0], [0, -1]]) + 0j)

        return unitary

    def _contr_sq_rot(self, lamda, theta, phi):
        """matrix representation of controlled single qubit gates
        using qiskits indexing of the qubits

        Parameters
        ----------
        lamda : float
            rotation angle
        theta : float
            azimuthal angle of the rotation axis
        phi : float
            polar angle of the rotation axis

        Returns
        -------
        np.array[float]
            4x4 np.array of the matrix representation of the controlled rotation
            matrix
        """

        unitary = np.zeros((4, 4)) + 0j
        unitary[0::2, 0::2] = np.eye(2)
        unitary[1::2, 1::2] = self._sq_rot(lamda, theta, phi)

        return unitary
