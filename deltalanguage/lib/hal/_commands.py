from enum import Enum
from typing import Iterable, List

from deltalanguage.data_types import DUInt, DSize, DArray

# Command fields
# 31-26       25-16        15-0
# [OPCODE]    [ARGUMENT]   [QUBIT INDEX]


class Opcode(Enum):
    """Operational codes for HAL."""

    NOP = 0
    STATE_PREPARATION = 1
    STATE_MEASURE = 2
    SEND_TO_HOST = 3
    STOP = 4

    H = 5
    R = 6
    RX = 7
    RY = 8
    RZ = 9
    S = 10
    SQRT_X = 11
    T = 12
    X = 13
    Y = 14
    Z = 15

    CONTROL = 16

    INVS = 17

    ID = 18  # identity gate
    SX = 19  # pi-rotation around x+y (required for randomized compiling)
    SY = 20  # pi-rotation around x-y (required for randomized compiling)

    # pi-rotations with axes in the xy, yz, and zx-planes, respectively
    PIXY = 21
    PIYZ = 22
    PIZX = 23


class Shifts(Enum):
    """
    .. TODO:: Missing description.
    """

    ARG = 16
    OPCODE = 26
    VALIDS = 16


class Masks(Enum):
    """
    .. TODO:: Missing description.
    """

    QUBIT_INDEX = 65535
    ARG = 67043328
    VALIDS = 4294901760
    MEASUREMENTS = 65535


def command_creator(op: str, argument=0, qubit=0) -> DUInt(DSize(32)):
    """Helper function to create HAL commands.

    Parameters
    ----------
    op : str
        Name of opcode.
    argument : int
        Integer representation of argument value
    qubit : int
        Integer representation of qubit address

    Returns
    -------
    DUInt(DSize(32))
        32-bit HAL command
    """
    return (Opcode[op].value << Shifts.OPCODE.value) \
        | (argument << Shifts.ARG.value) | qubit


def command_unpacker(cmd: DUInt(DSize(32))):
    """Helper function to unpack HAL commands.

    Parameters
    ----------
    cmd : DUInt(DSize(32))
        32-bit HAL command.

    Returns
    -------
    op : str
        Name of opcode.
    argument : int
        Integer representation of argument value.
    qubit : int
        Integer representation of qubit address.
    """
    op_mask = sum(map(lambda n: 2**n, range(Shifts.OPCODE.value, 32)))
    op = (cmd & op_mask) >> Shifts.OPCODE.value
    # We pass strings around rather than Opcode elements, so we use
    # this to get the reverse mapping from the Opcode class
    # This is semi-safe, as we don't have repeated names for operations
    op = Opcode._value2member_map_[op]._name_

    arg_mask = sum(map(lambda n: 2**n,
                       range(Shifts.ARG.value, Shifts.OPCODE.value)))
    arg = (cmd & arg_mask) >> Shifts.ARG.value

    qubit_mask = sum(map(lambda n: 2**n, range(0, Shifts.VALIDS.value)))
    qubit = (cmd & qubit_mask)
    return (op, arg, qubit)


def measurement_unpacker(bitcode: DUInt(DSize(32)), qubits: Iterable) -> List:
    """Helper function to convert 32-bit status result from HAL into an array
    of measurements for given qubit indices.

    Parameters
    ----------
    bitcode : DUInt(DSize(32))
        32-bit measurement status from HAL.
    qubits : Iterable
        List of qubits for which the measurement result will be returned.

    Returns
    -------
    List
        List of measurement results for the specified qubits.

    Raises
    ------
    ValueError
        If not all valid flags are 1.
    """

    # split status bitcode into measurements (first 16 bits) and
    # valid flags (last 16 bits)
    measurements = bitcode & Masks.MEASUREMENTS.value
    valids = (bitcode & Masks.VALIDS.value) << Shifts.VALIDS.value

    # print('1', measurements)

    if valids != Masks.VALIDS.value << Shifts.VALIDS.value:
        raise ValueError(f"Invalid measurement!, {hex(valids)}, "
                         f"{hex(Masks.VALIDS.value << Shifts.VALIDS.value)}")

    measurements_list = []

    for i in qubits:
        measurements_list.append((measurements >> i) & 1)

    # print('2', measurements_list)
    return measurements_list


def measurement_creator(measurement_array, qubits):
    """Helper function to convert 32-bit status result from HAL into an array
    of measurements for given qubit indices.

    Parameters
    ----------
    measurement_array
        List of measurement results for the specified qubits.
    qubits : Iterable
        List of qubits for which the measurement result will be returned.

    Returns
    -------
    bitcode : DUInt(DSize(32))
        32-bit measurement status from HAL.
    """
    packed_measurements = 0
    for i in qubits:
        measurement = measurement_array.pop()
        packed_measurements |= 2**i if measurement else 0

    packed_measurements |= Masks.VALIDS.value

    return packed_measurements
