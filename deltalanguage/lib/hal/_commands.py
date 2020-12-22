from enum import Enum

from deltalanguage.data_types import DUInt, DSize, DArray

# Command fields
# 31-26       25-16        15-0
# [OPCODE]    [ARGUMENT]   [QUBIT INDEX]


class Opcode(Enum):
    """Operational codes for HAL.

    .. note:: Not user-facing class.
    """

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

    .. note:: Not user-facing class.
    """

    ARG = 16
    OPCODE = 26
    VALIDS = 16


class Masks(Enum):
    """
    .. TODO:: Missing description.

    .. note:: Not user-facing class.
    """

    QUBIT_INDEX = 65535
    ARG = 67043328
    VALIDS = 4294901760
    MEASUREMENTS = 65535


def command_creator(op: str, argument=0, qubit=0) -> DUInt(DSize(32)):
    """Helper function to create HAL commands.

    .. TODO:: Eventually will be inside DType classes, so can remove later.

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


def measurement_unpacker(bitcode: DUInt(DSize(32)), qubits: DArray) -> DArray:
    """Helper function to convert 32-bit status result from HAL into an array
    of measurements for given qubit indices.

    .. TODO::
        Replace ``DArray`` by either ``object`` or specify its type and
        length.


    Parameters
    ----------
    bitcode : DUInt(DSize(32))
        32-bit measurement status from HAL.
    qubits : DArray
        List of qubits for which the measurement result will be returned.

    Raises
    ------
    ValueError
        If not all valid flags are 1.


    Returns
    -------
    DArray
        List of measurement results for the specified qubits.
    """

    # split status bitcode into measurements (first 16 bits) and
    # valid flags (last 16 bits)
    measurements = bitcode & Masks.MEASUREMENTS.value
    valids = (bitcode & Masks.VALIDS.value) << Shifts.VALIDS.value

    # print('1', measurements)

    if valids != Masks.VALIDS.value << Shifts.VALIDS.value:
        raise ValueError("Invalid measurement!")

    measurements_list = []

    for i in qubits:
        measurements_list.append((measurements >> i) & 1)

    # print('2', measurements_list)
    return measurements_list
