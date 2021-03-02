"""
The standard library for the Deltaflow language contains:

- Primitives for generation, re-routing, and collection of data:
  :py:func:`make_generator`
  :py:func:`make_splitter`
  :py:class:`StateSaver`

- Routines for the Hardware Abstraction Layer (HAL) and Quantum Simulators,
  which are best described in :doc:`examples/examples`.
"""

from deltalanguage.lib.hal import (HardwareAbstractionLayerNode,
                                   Masks,
                                   Opcode,
                                   Shifts,
                                   command_creator,
                                   measurement_unpacker)
from deltalanguage.lib.primitives import (make_generator,
                                          make_splitter,
                                          StateSaver)
from deltalanguage.lib.quantum_simulators import (IQuantumSimulator,
                                                  ProjectqQuantumSimulator,
                                                  QiskitQuantumSimulator)
