# README

This file includes some instructions and guidelines how to use the Qiskit 
backend of the HAL and the related noise model. 

## Qiskit backend

The Qiskit backend `_qiskit_quantum_simulator.py` presents an alternative 
to the project Q backend `_projectq_quantum_simulator.py` that comes with the 
same functionalities. Additionally, the Qiskit backend supports simulation 
methods of noisy quantum circuits using a `CustomNoiseModel` class defined in
 `_qiskit_noise_model.py`.

The noise model currently supports the following types of errors: 

- Coherent over-rotations of each single- and two-qubit gates
- single- and two-qubit depolarization noise channels
- single-qubit amplitude and phase damping channels
- single-qubit thermal relazation channels

The relevant parameters for these noise types are given by the user when 
initializing a noise model object:
 
```python
from deltalanguage.lib.quantum_simulators import (QiskitQuantumSimulator,
                                                  CustomNoiseModel)

noise = CustomNoiseModel(
    coherent_error_angles=[0.2, 0.1], # adding coherent errors
    depol_errors=[0.02, 0.02], # adding depolarization error
    damping_params=[0.1, 0.1, 0.1], # adding amplitude and phase damping
    relaxation_params=[0.1, 0.15, 0.1, 0.1] # adding thermal relazation
)
```
As `CustomNoideModel` inherits from Qiskit's `NoiseModel` class, additional 
error types can be added manually as usual in qiskit, for example:

```python
# Add depolarizing error to all hadamard gates on qubit 0 only
error = depolarizing_error(0.05, 1)
noise_model.add_quantum_error(error, ['h'], [0])
```

### Adding new gates

When executing a circuit, the qiskit backend will apply the errors to all gates 
defined in the HAL. For this prupose, all gates in the HAL need to have a qiskit
 `label` that is set within the `CustomNoiseModel` class.

Currently these labels are the following: 

```python
>>> empty_noise = CustomNoiseModel()
    print(empty_noise._sq_gates)
    print(empty_noise._tq_gates)
```
```
['h', 'PiXY', 'PiYZ', 'PiZX', 'R', 'RX', 'RY', 'RZ', 's', 'sdg', 'sqrt_x', 'SX',
 'SY', 't', 'X', 'Y', 'Z']
['cx', 'cy', 'cz']
```

If you wish to add new gates to the HAL backend and simulate noise on them, you 
need to assign a Qiskit label to it and add this label to the above `_sq_gates` 
or `_tq_gates` properties. For instance a gate can be defined in the 
`_qiskit_quantum_simulator.py` from a unitary matrix as:

```python
class SxGate(UnitaryGate):
    def __init__(self):
        super().__init__(np.array([[0, 1], [1j, 0]]), label='SX')
```
Noise will be applied to this gate only if its label 'SX' is added to the list 
of single qubit labels above. 

#### Controlled gates

Like the projectQ backend, the Qiskit backend supports controlled gates 
(also with multiple control qubits) by giving 'CONTROL' commands followed by a 
single-qubit gate. However, noise can only be simulated on (singly) 
controlled-X, controlled-Y and controlled-Z gates.

If you wish to add noise to a more involved controlled gate, this gate needs to
 be defined as a gate object, given a Qiskit label and this label needs to be 
 added to the two-qubit label list `_tq_gates`.