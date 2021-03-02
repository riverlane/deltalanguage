"""Characterization test BaseDeltaType and its subclasses."""

import random
import unittest

import attr
import numpy as np

from deltalanguage.lib.hal._commands import *


class DeltaHALTest(unittest.TestCase):
    """The most basic tests of BaseDeltaType outside of the context of
    wires (streams, channels) and DeltaGraph.
    """

    def test_roundtrip_hal_commands(self):
        """Test roundtripping of the command packer/unpackers."""
        for opcode in Opcode.__members__.keys():
            for qubit in range(8):
                for arg in range(128):
                    self.assertEqual(
                        command_unpacker(command_creator(opcode, arg, qubit)),
                        (opcode, arg, qubit)
                    )

    def test_roundtrip_measurements_4q(self):
        """Test roundtripping of the command packer/unpackers."""
        test_list = [((Masks.VALIDS.value) | int("0000000000000110", base=2),
                      [0, 1, 2, 3])]
        for bitcode, qubits in test_list:
            rt_bitcode = measurement_creator(
                measurement_unpacker(bitcode, qubits), qubits)
            self.assertEqual(rt_bitcode, bitcode)


if __name__ == "__main__":
    unittest.main()
