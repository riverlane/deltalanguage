"""Types that cannot actually be used as python types.
They do not integrate with mypy.
They do not have values you can interact with.
"""

from abc import ABC, abstractmethod
import logging
import struct
import typing

import attr
import numpy as np

from deltalanguage.logging import make_logger

from ._exceptions import DeltaTypeError
from ._special import Size, Void

logger = make_logger(logging.WARNING, "Data Types")


class BaseDeltaType(ABC):
    """The base Deltaflow type, of which other types are derived.

    Attributes
    ----------
    size : Size
        Full size of the data type. There are several cases:

        * for primitive types it's the number of bits
        * for compound types it's the sum of all componenets' sizes
        * for :py:class:`Union` that is the the size of the largest element
          PLUS 1 byte that stores which particular data type is encoded
    """

    def __init__(self):
        self._pack_format = None
        self.size = Size(0)

    def bytes_to_bits(self, s: bytes) -> bytes:
        """Converts a byte encoding of an object to a bit encoding.

        Parameters
        ----------
        s : bytes
            The object encoded as a byte string.

        Returns
        -------
        bytes
            The same object encoded as a bit string.
        """
        if s == "":
            return ""
        return format(int.from_bytes(s, byteorder="little"),
                      f'0{self.size}b').encode("ascii")

    def bits_to_bytes(self, s: bytes) -> bytes:
        """Converts a bit string encoding of an object to a byte string.

        Parameters
        ----------
        s : bytes
            Bit string encoding of an object.

        Returns
        -------
        bytes
            The same object encoded as a byte string.
        """
        return int(s.decode("ascii"), 2).to_bytes((len(s) + 7) // 8, 'little')

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def as_python_type(self) -> typing.Type:
        """Returns the equivalent Python data type.

        For compound data structures this method will be called
        recursively for all subcomponents.

        .. note::
            Python types do not support the idea of fixed size, thus this
            mapping is surjective, for instance ``Int(Size(32))`` and
            ``Int(Size(64))`` both are mapped to ``int``.
        """
        pass

    @abstractmethod
    def as_numpy_type(self) -> typing.Type:
        """Returns an equivalent NumPy data type.

        For compound data structures this method will be called
        recursively for all subcomponents.

        .. note::
            NumPy types only support limited fixed sizes. For instance,
            ``UInt(Size(8))`` is compatible with ``numpy.uint8``,
            but ``UInt(Size(128))`` has no compatible numpy type.
        """
        pass

    @abstractmethod
    def as_numpy_object(self, val):
        """Returns a NumPy object set to val.

        For primitive delta types, this is the equivalent Python type.
        For compound types, this is a Numpy array whose elements are
        the corresponding types.
        """
        pass

    @abstractmethod
    def from_numpy_object(self, val):
        """Given a NumPy object, converts to an equivalent Python object.

        .. warning::
            Only one-dimensional NumPy arrays are currently supported.
        """
        pass

    def __repr__(self):
        return str(self)

    @abstractmethod
    def pack(self, val: object) -> bytes:
        """Encode an object to a bit string.

        For compound data structures this method will be called
        recursively for all subcomponents.

        Parameters
        ----------
        val : object
            Object to be packed.
            Its type should match :py:meth:`as_python_type`.

        Returns
        -------
        bytes
        """
        pass

    @abstractmethod
    def unpack(self, buffer: bytes) -> object:
        """Decode bit string to an object.

        Parameters
        ----------
        bytes
            Bytestring with a packed object of the class.

        Returns
        -------
        object
            Object itself.
        """
        pass

    @abstractmethod
    def is_packable(self, val: object) -> bool:
        """Checks if the object can be packed as this type.

        Parameters
        ----------
        val : object
            Object to be packed.

        Returns
        -------
        bool
            True if the object can be packed as this type, otherwise False.
        """

    @property
    def pack_format(self):
        """Format for :py:func:`struct.pack` defined by
        :py:meth:`set_pack_format`.

        Return
        ------
        str
        """
        if self._pack_format is None:
            self.set_pack_format()
        return self._pack_format

    @abstractmethod
    def set_pack_format(self):
        """Set :py:attr:`pack_format`.

        .. todo::
            This can be implemented via `@property.setter`.
        """
        pass


class PrimitiveDeltaType(BaseDeltaType):
    """Primitive Deltaflow types, which have a direct mapping to primitive
    types of Python and C.
    """

    def __eq__(self, other):
        if type(self) is type(other):
            return self.size == other.size
        return False

    def __hash__(self):
        return hash(self.size)

    def pack(self, val):
        return self.bytes_to_bits(struct.pack(self.pack_format, val))

    def unpack(self, buffer):
        return struct.unpack(self.pack_format, self.bits_to_bytes(buffer))[0]

    def as_numpy_object(self, val):
        return self.as_numpy_type()(val)

    def from_numpy_object(self, val):
        return self.as_python_type()(val)

    def is_packable(self, val):
        try:
            self.pack(val)
            return True
        except:
            return False


class CompoundDeltaType(BaseDeltaType):
    """Compound Deltaflow types are constucted using primitive data types."""

    @abstractmethod
    def __len__(self):
        pass

    @abstractmethod
    def __hash__(self):
        pass

    @abstractmethod
    def flatten(self, vals) -> list:
        """Converts data of this type to a plain list."""
        pass

    @abstractmethod
    def deflatten(self, flatten_vals: list):
        """Reverts :py:meth:`flatten`. The return type is exactly the same as
        :py:meth:`as_python_type` for each data type.
        """
        pass


class Top(BaseDeltaType):
    """Default Deltaflow type. Used if type is not recognised.
    Defined as a singleton.
    """

    _instance = None

    # allocation for a generic object size
    size = Size(100000)

    def __new__(cls):
        """If a Top object type already exists, return that type.
        Otherwise, generate a Top object type.
        Based on https://python-patterns.guide/gang-of-four/singleton/

        Returns
        -------
            A Deltaflow Top type.
        """
        if cls._instance is None:
            # Use BaseDeltaType __new__ function to construct a Top object.
            cls._instance = super(Top, cls).__new__(cls)
        return cls._instance

    def __str__(self):
        return "T"

    def as_python_type(self):
        return typing.Any

    def as_numpy_type(self):
        raise NotImplementedError

    def as_numpy_object(self, val):
        raise NotImplementedError

    def from_numpy_object(self, val):
        raise NotImplementedError

    def pack(self, val):
        raise NotImplementedError

    def unpack(self, buffer):
        raise NotImplementedError

    def is_packable(self, val):
        raise NotImplementedError

    def set_pack_format(self):
        raise NotImplementedError


class Array(CompoundDeltaType):
    """Fixed-size collection of objects of the same type.

    Parameters
    ----------
    list_of : typing.Union[typing.Type, BaseDeltaType]
        typing.Type of elements. Note that elements can be of both primitive and
        compound types.
    length : Size
        Number of elements.
    """

    def __init__(self, list_of: typing.Union[typing.Type, BaseDeltaType], length: Size):
        if not isinstance(length, Size):
            raise DeltaTypeError("Length needs to be Size.")
        super().__init__()
        self.list_of = as_delta_type(list_of)
        if self.list_of == Top():
            raise DeltaTypeError("Array type cannot be Top().")
        self.length = length
        self.size = self.list_of.size * self.length

    def __str__(self):
        return f"[{self.list_of} x {self.length}]"

    def __len__(self):
        return self.length

    def as_python_type(self):
        # python does not have fixed size typing.List
        return typing.List[self.list_of.as_python_type()]

    def as_numpy_object(self, val):
        return np.array([self.list_of.as_numpy_object(v) for v in val],
                        dtype=self.list_of.as_numpy_type())

    def from_numpy_object(self, val):
        if type(val) is not np.ndarray:
            # Array is wrapped in a tuple object
            if len(val) != 1:
                logger.warning(
                    "Warning, NumPy array object for Array has length != 1")
            val = val[0]
        return [self.list_of.from_numpy_object(v) for v in val]

    def as_numpy_type(self):
        return np.dtype([('f0',
                          self.list_of.as_numpy_type(),
                          self.length.val)])

    def __eq__(self, other):
        if type(self) is type(other):
            return self.list_of == other.list_of and self.length == other.length
        return False

    def __hash__(self):
        return hash((self.list_of, self.length))

    def flatten(self, vals):
        flatten_vals = []
        for v in vals:
            v_df_type = delta_type(v)
            if is_primitive(v_df_type):
                flatten_vals.append(v)
            else:
                flatten_vals += v_df_type.flatten(v)
        return flatten_vals

    def deflatten(self, flatten_vals):
        vals = []
        if is_primitive(self.list_of):
            for _ in range(self.length.val):
                # TODO pop from the end would be better
                vals.append(flatten_vals.pop(0))
        else:
            for _ in range(self.length.val):
                vals.append(self.list_of.deflatten(flatten_vals))

        return vals

    def pack(self, val):
        if not self.is_packable(val):
            raise DeltaTypeError(f'Data does not match the packing format\n'
                                 f'{val=}\n{self=}')

        if type(val) is np.ndarray:
            val = self.from_numpy_object(val)

        return b"".join([self.list_of.pack(v) for v in val])

    def unpack(self, buffer):
        return [self.list_of.unpack(buffer[i:i+self.list_of.size.val])
                for i in range(0, len(buffer), self.list_of.size.val)]

    def is_packable(self, val):
        if not isinstance(val, (typing.List, np.ndarray)):
            return False
        elif len(val) == self.length.val:
            return all(self.list_of.is_packable(v) for v in val)
        else:
            return False

    def set_pack_format(self):
        self._pack_format = self.list_of.pack_format * self.length.val


class UInt(PrimitiveDeltaType):
    """Unsigned integers with a given number of bits.

    Parameters
    ----------
    size : Size
        Full size of the data type.
    """

    def __init__(self, size: Size = Size(32)):
        if not isinstance(size, Size):
            raise DeltaTypeError
        super().__init__()
        self.size = size

    def __str__(self):
        return f"UInt{self.size}"

    def as_python_type(self):
        return int

    def as_numpy_type(self):
        if self.size == Size(8):
            return np.uint8
        elif self.size == Size(16):
            return np.uint16
        elif self.size == Size(32):
            return np.uint32
        elif self.size == Size(64):
            return np.uint64
        else:
            raise NotImplementedError(f'Unsupported format: {self.size} - '
                                      'supported sizes are 8, 16, 32, 64')

    def set_pack_format(self):
        if self.size == Size(8):
            self._pack_format = 'B'
        elif self.size == Size(16):
            self._pack_format = 'H'
        elif self.size == Size(32):
            self._pack_format = 'I'
        elif self.size == Size(64):
            self._pack_format = 'Q'
        else:
            raise NotImplementedError(f'Unsupported format: {self.size} - '
                                      'supported sizes are 8, 16, 32, 64')


class Int(PrimitiveDeltaType):
    """Signed integers with a given number of bits.

    Parameters
    ----------
    size : Size
        Full size of the data type.
    """

    def __init__(self, size: Size = Size(32)):
        if not isinstance(size, Size):
            raise DeltaTypeError
        super().__init__()
        self.size = size

    def __str__(self):
        return f"Int{self.size}"

    def as_python_type(self):
        return int

    def as_numpy_type(self):
        if self.size == Size(8):
            return np.int8
        elif self.size == Size(16):
            return np.int16
        elif self.size == Size(32):
            return np.int32
        elif self.size == Size(64):
            return np.int64
        else:
            raise NotImplementedError(f'Unsupported format: {self.size} - '
                                      'supported sizes are 8, 16, 32, 64')

    def set_pack_format(self):
        if self.size == Size(8):
            self._pack_format = 'b'
        elif self.size == Size(16):
            self._pack_format = 'h'
        elif self.size == Size(32):
            self._pack_format = 'i'
        elif self.size == Size(64):
            self._pack_format = 'q'
        else:
            raise NotImplementedError(f'Unsupported format: {self.size} - '
                                      'supported sizes are 8, 16, 32, 64')


class Bool(PrimitiveDeltaType):
    """Boolean 1-bit type."""

    def __init__(self):
        super().__init__()
        self.size = Size(1)

    def __str__(self):
        return "Bool"

    def as_python_type(self):
        return bool

    def as_numpy_type(self):
        return np.bool_

    def set_pack_format(self):
        self._pack_format = '?'

    def pack(self, val):
        if val == True:
            return b'1'
        elif val == False:
            return b'0'
        else:
            raise DeltaTypeError

    def unpack(self, buffer):
        if buffer == b'0':
            return False
        elif buffer == b'1':
            return True
        else:
            raise DeltaTypeError


class Char(PrimitiveDeltaType):
    """Character implemented via 8-bit in analogy with ``char`` from ``struct``
    library.
    """

    def __init__(self):
        super().__init__()
        self.size = Size(8)

    def __str__(self):
        return "Char8"

    def as_python_type(self):
        raise NotImplementedError('Python does not have char type')

    def as_numpy_type(self):
        return np.uint8

    def as_numpy_object(self, val):
        return np.ubyte(ord(val))

    def from_numpy_object(self, val):
        return chr(val)

    def pack(self, val):
        return super().pack(val.encode('ascii'))

    def unpack(self, val):
        return super().unpack(val.decode('ascii'))

    def set_pack_format(self):
        self._pack_format = 'c'


class Str(Array):
    """Array of characters."""

    def __init__(self, length: Size = Size(1024)):
        if not isinstance(length, Size):
            raise DeltaTypeError
        super().__init__(Char(), length)

    def __str__(self):
        return f"Str{self.size}"

    def as_python_type(self):
        return str

    def as_numpy_type(self):
        return (np.string_, self.length.val)

    def as_numpy_object(self, val):
        return np.string_(val)

    def from_numpy_object(self, val):
        return val.decode("ascii")

    def flatten(self, vals):
        return [vals.encode('ascii')]

    def deflatten(self, flatten_vals):
        val = flatten_vals.pop(0)
        return val.decode('ascii').rstrip('\x00')

    def pack(self, val):
        # overwrite
        if not self.is_packable(val):
            raise DeltaTypeError(f'Data does not match the packing format\n'
                                 f'{val=}\n{self=}')

        if type(val) is np.string_:
            val = self.from_numpy_object(val)
        return self.bytes_to_bits(struct.pack(self.pack_format,
                                              *self.flatten(val)))

    def unpack(self, buffer):
        # overwrite
        flatten_vals = list(struct.unpack(self.pack_format,
                                          self.bits_to_bytes(buffer)))
        return self.deflatten(flatten_vals)

    def is_packable(self, val):
        val_df_type = delta_type(val)
        if type(val_df_type) is Str and val_df_type.length <= self.length:
            return True
        elif type(val_df_type) is Char:
            return True
        else:
            return False

    def set_pack_format(self):
        self._pack_format = str(self.length) + 's'


class Float(PrimitiveDeltaType):
    """Floating point numbers.

    For the concrete implementation of encoding see ``struct``, in particular
    the packing uses IEEE 754 with a single integer number for the size.
    """

    def __init__(self, size: Size = Size(32)):
        if not isinstance(size, Size):
            raise DeltaTypeError
        super().__init__()
        self.size = size

    def __str__(self):
        return f"Float{self.size}"

    def as_python_type(self):
        return float

    def as_numpy_type(self):
        if self.size == Size(32):
            return np.float32
        elif self.size == Size(64):
            return np.float64
        else:
            raise NotImplementedError(f'Unsupported format: {self.size} - '
                                      'supported sizes are 32, 64')

    def set_pack_format(self):
        if self.size == Size(32):
            self._pack_format = 'f'
        elif self.size == Size(64):
            self._pack_format = 'd'
        else:
            raise NotImplementedError(f'Unsupported format: {self.size} - '
                                      'supported sizes are 32, 64')


class Complex(PrimitiveDeltaType):
    """Complex numbers are implemented as two floating point numbers
    for real and imaginary components.
    """

    def __init__(self, size: Size = Size(64)):
        if not isinstance(size, Size):
            raise DeltaTypeError
        super().__init__()
        self.size = size

    def __str__(self):
        return f"Complex{self.size}"

    def as_python_type(self):
        return complex

    def as_numpy_type(self):
        if self.size == Size(64):
            return np.complex64
        elif self.size == Size(128):
            return np.complex128
        else:
            raise NotImplementedError(f'Unsupported format: {self.size} - '
                                      'supported sizes are 64, 128')

    def set_pack_format(self):
        if self.size == Size(64):
            self._pack_format = 'ff'
        elif self.size == Size(128):
            self._pack_format = 'dd'
        else:
            raise NotImplementedError(f'Unsupported format: {self.size} - '
                                      'supported sizes are 64, 128')

    def pack(self, val):
        return self.bytes_to_bits(struct.pack(self.pack_format,
                                              val.real,
                                              val.imag))

    def unpack(self, buffer):
        vals = struct.unpack(self.pack_format, self.bits_to_bytes(buffer))
        return vals[0] + vals[1] * 1j


class Tuple(CompoundDeltaType):
    """Fixed collection of items of different types."""

    def __init__(self, elems: typing.Iterable[typing.Union[typing.Type, BaseDeltaType]]):
        super().__init__()
        elem_list = []

        for elem in elems:
            elem_list.append(as_delta_type(elem))
        if Top() in elem_list:
            raise DeltaTypeError("Tuple cannot contain Top.")

        self.elems = tuple(elem_list)
        if len(self) == 0:
            raise ValueError("You cannot have empty Tuple")

        self.size = sum((e.size for e in self.elems), Size(0))

    def __str__(self):
        return f"({', '.join(map(str, self.elems))})"

    def __len__(self):
        return len(self.elems)

    def as_python_type(self):
        return typing.Tuple[tuple([t.as_python_type() for t in self.elems])]

    def as_numpy_object(self, val):
        m = np.zeros(1, dtype=[(f"f{i}", t.as_numpy_type())
                               for i, t in enumerate(self.elems)])
        for i, (v, t) in enumerate(zip(val, self.elems)):
            if type(t) is Array:
                m[0][i][0][:] = t.as_numpy_object(v)
            else:
                m[0][i] = t.as_numpy_object(v)
        return m

    def from_numpy_object(self, val):
        if type(val) is np.ndarray:
            # Get first row of array
            if len(val) != 1:
                logger.warning(
                    "Warning, NumPy array object for Tuple has length != 1")
            val = val[0]
        return tuple((t.from_numpy_object(v))
                     for t, v in zip(self.elems, val))

    def as_numpy_type(self):
        return np.dtype([(f'f{i}', t.as_numpy_type())
                         for i, t in enumerate(self.elems)])

    def __eq__(self, other):
        if type(other) is Tuple:
            return self.elems == other.elems
        return False

    def __hash__(self):
        return hash(self.elems)

    def flatten(self, vals):
        flatten_vals = []
        for v in vals:
            v_df_type = delta_type(v)
            if is_primitive(v_df_type):
                flatten_vals.append(v)
            else:
                flatten_vals += v_df_type.flatten(v)
        return flatten_vals

    def deflatten(self, flatten_vals):
        vals = []
        for e in self.elems:
            if is_primitive(e):
                # TODO pop from the end would be better
                vals.append(flatten_vals.pop(0))
            else:
                vals.append(e.deflatten(flatten_vals))

        # matches the type of unpack
        return tuple(vals)

    def pack(self, val):
        if not self.is_packable(val):
            raise DeltaTypeError(f'Data does not match the packing format\n'
                                 f'{val=}\n{self=}')

        if type(val) is np.ndarray:
            val = self.from_numpy_object(val)

        return b"".join([t.pack(v) for t, v in zip(self.elems, val)])

    def unpack(self, buffer):
        vals = []
        for t in self.elems:
            vals.append(t.unpack(buffer[:t.size.val]))
            buffer = buffer[t.size.val:]
        return tuple(vals)

    def is_packable(self, val):
        t = delta_type(val)
        if type(t) is Tuple and len(t.elems) == len(self.elems):
            if type(val) is np.ndarray:
                # Get first row of array
                if len(val) != 1:
                    logger.warning(
                        "NumPy array object for Tuple has length != 1")
                val = val[0]
            return all(elem.is_packable(v) for elem, v in zip(self.elems, val))
        return False

    def set_pack_format(self):
        self._pack_format = "".join((e.pack_format for e in self.elems))


class Record(CompoundDeltaType):
    """Records are ordered collections of key-value pairs, with the key
    being a string and the value being of a given type.

    Parameters
    ----------
    attrs_type
        Class defined via ``attrs`` library, see examples.

    Examples
    --------
    A data container class created with ``attrs`` used for keyworded
    data transfer:

    .. code-block:: python

        >>> import attr
        >>> import deltalanguage as dl

        >>> @attr.s(slots=True)
        ... class RecBI:
        ...
        ...     x: bool = attr.ib()
        ...     y: int = attr.ib()

        >>> dl.Record(RecBI)
        {x: Bool, y: Int32}
    """

    def __init__(self, attrs_type):
        if not attr.has(attrs_type):
            raise DeltaTypeError('Please provide class with attrs attributes')
        super().__init__()
        self.attrs_type = attrs_type

        if hasattr(attrs_type, "__annotations__"):
            elem_list = [(name, as_delta_type(t))
                         for name, t in attrs_type.__annotations__.items()]
        else:
            # Used if attrs_type constructed via make_class
            elem_list = [(a.name, as_delta_type(a.type))
                         for a in attrs_type.__attrs_attrs__]

        if not elem_list:
            raise ValueError("You cannot have empty record types.")
        if Top() in [elem[1] for elem in elem_list]:
            raise DeltaTypeError("Record cannot contain Top.")

        names = [n for (n, _) in elem_list]
        if len(names) != len(set(names)):
            raise ValueError("Matching keys.")

        self.elems = tuple(elem_list)
        self.size = sum((e.size for (_, e) in self.elems), Size(0))

    def __str__(self):
        def record_inst_printer(field):
            return f"{field[0]}: {field[1]}"
        return f"{{{', '.join(map(record_inst_printer, self.elems))}}}"

    def __len__(self):
        return len(self.elems)

    def as_python_type(self):
        # if attrs_type has delta types, they won't be converted to python
        return self.attrs_type

    def as_numpy_object(self, val):
        m = np.zeros(1, dtype=[(name, t.as_numpy_type())
                               for name, t in self.elems])
        for name, t in self.elems:
            if type(t) is Array:
                m[0][name][0][:] = t.as_numpy_object(getattr(val, name))
            else:
                m[0][name] = t.as_numpy_object(getattr(val, name))

        return np.rec.array(m)

    def from_numpy_object(self, val):
        if isinstance(val, np.ndarray):
            # Get first row of array
            if len(val) != 1:
                logger.warning(
                    "Warning, NumPy array object for Record has length != 1")
            val = val[0]
        return self.attrs_type(*[t.from_numpy_object(val[name])
                                 for name, t in self.elems])

    def as_numpy_type(self):
        return np.dtype((np.record, [(name, t.as_numpy_type())
                                     for name, t in self.elems]))

    def __eq__(self, other):
        if type(self) is type(other):
            return self.elems == other.elems
        return False

    def __hash__(self):
        return hash(self.elems)

    def flatten(self, vals):
        flatten_vals = []
        for v in attr.astuple(vals, retain_collection_types=True):
            v_df_type = delta_type(v)
            if is_primitive(v_df_type):
                flatten_vals.append(v)
            else:
                flatten_vals += v_df_type.flatten(v)
        return flatten_vals

    def deflatten(self, flatten_vals):
        vals = []
        for (_, e) in self.elems:
            if is_primitive(e):
                # TODO pop from the end would be better
                vals.append(flatten_vals.pop(0))
            else:
                vals.append(e.deflatten(flatten_vals))

        # matches the type of unpack
        return self.attrs_type(*vals)

    def pack(self, val):
        if not self.is_packable(val):
            raise DeltaTypeError(f'Data does not match the packing format\n'
                                 f'{val=}\n{self=}')

        if isinstance(val, np.ndarray):
            val = self.from_numpy_object(val)

        return b"".join(
            [t[1].pack(v)
             for t, v in
             zip(self.elems, attr.astuple(val, retain_collection_types=True))])

    def unpack(self, buffer):
        vals = []
        for _, t in self.elems:
            vals.append(t.unpack(buffer[:t.size.val]))
            buffer = buffer[t.size.val:]
        return self.attrs_type(*vals)

    def is_packable(self, val):
        if isinstance(val, np.ndarray):
            # Get first row of NumPy array and load into attrs_type object
            if len(val) != 1:
                logger.warning(
                    "Warning, NumPy array object for Record has length != 1")
            val = self.attrs_type(*val[0])
        if attr.has(val):
            if len(attr.astuple(val)) != len(self.elems):
                return False

            def packable_attrs(name, t):
                return hasattr(val, name) and t.is_packable(getattr(val, name))
            return all(packable_attrs(name, t) for name, t in self.elems)
        else:
            return False

    def set_pack_format(self):
        self._pack_format = "".join(
            (e.pack_format for (_, e) in self.elems))


class Union(CompoundDeltaType):
    """Container for several Deltaflow types.

    Parameters
    ----------
    elems : typing.Iterable[typing.Union[typing.Type, BaseDeltaType]]
        Data types.

    Examples
    --------
    .. code-block:: python

        >>> import deltalanguage as dl

        >>> dl.Union([int, bool])
        <Bool | Int32>

    Note that the order or elements does not matter:

    .. code-block:: python

        >>> dl.Union([int, bool]) == dl.Union([bool, int])
        True
    """

    def __init__(self, elems: typing.Iterable[typing.Union[typing.Type, BaseDeltaType]]):
        super().__init__()
        self.elems = []

        # flatten Unions and save only unique sorted elements
        for e in elems:
            if type(e) is Union:
                for ee in e.elems:
                    self._add_elem(as_delta_type(ee))
            else:
                self._add_elem(as_delta_type(e))

        if len(self.elems) == 0:
            raise DeltaTypeError("You cannot have empty Union")

        if Top() in self.elems:
            raise DeltaTypeError("Record cannot contain Top.")

        # 8 bits to encode meta data
        self.meta = UInt(Size(8))
        self.size = self.meta.size + max(e.size for e in self.elems)

    def __str__(self):
        elems_str = ' | '.join(map(str, self.elems))
        return '<' + elems_str + '>'

    def __len__(self):
        return len(self.elems)

    def as_python_type(self):
        constituent_py_types = [t.as_python_type() for t in self.elems]
        return typing.Union[tuple(constituent_py_types)]

    def as_numpy_object(self, val):
        array = np.zeros(1, dtype=self.as_numpy_type())
        for i, t in enumerate(self.elems):
            if t.is_packable(val):
                if type(t) is Array:
                    array[0][i][0][:] = t.as_numpy_object(val)
                else:
                    array[0][i] = t.as_numpy_object(val)
        return array

    def from_numpy_object(self, val):
        """
        .. warning::
            While ``Union`` objects can be converted to NumPy objects, they
            cannot be converted back. This is because NumPy unions do not
            specify which type is being used.
        """
        raise DeltaTypeError(
            "NumPy unions cannot be converted to Python types.")

    def as_numpy_type(self):
        # Unions are implemented as a NumPy array
        # where all elements have the same offset.
        return np.dtype({'names': [str(elem) for elem in self.elems],
                         'formats': [t.as_numpy_type() for t in self.elems],
                         'offsets': [0]*len(self.elems)})

    def _add_elem(self, elem: BaseDeltaType):
        if not elem in self.elems:
            self.elems.append(elem)
            self.elems.sort(key=str)

    def __eq__(self, other):
        if type(self) is type(other):
            return self.elems == other.elems
        return False

    def __hash__(self):
        return hash(tuple(self.elems))

    def flatten(self, vals):
        # no need, instead the same method from the identified type is used
        raise NotImplementedError

    def deflatten(self, flatten_vals):
        # no need, instead the same method from the identified type is used
        raise NotImplementedError

    def pack(self, val):
        if type(val) is np.ndarray:
            raise DeltaTypeError(
                "NumPy unions cannot be converted to Python types.")
        for i, elem in enumerate(self.elems):
            if elem.is_packable(val):
                val_df_type = self.elems[i]
                # append empty bytes so buffer is always the same
                pad_len = self.size - self.meta.size - val_df_type.size
                if pad_len:
                    padding = b'0' * (pad_len).val
                else:
                    padding = ''
                buffer = val_df_type.pack(val) \
                    + padding \
                    + self.meta.pack(i)

                if len(buffer) != self.size.val:
                    raise ValueError(
                        f'Buffer size mismatch: {val}, {self.size.val}')

                return buffer

        raise DeltaTypeError(f'Union does not support {val}')

    def unpack(self, buffer):
        val_df_type_idx = self.meta.unpack(buffer[-8:])
        val_df_type = self.elems[val_df_type_idx]

        # pick the appropriate number of bytes
        val = val_df_type.unpack(
            buffer[:self.elems[val_df_type_idx].size.val]
        )

        return val  # -> can be any supported type

    def is_packable(self, val):
        if type(val) is np.ndarray:
            return False
        return any(elem.is_packable(val) for elem in self.elems)

    def set_pack_format(self):
        # the data format is encoded in the 1-byte meta buffer
        pass


class Raw(BaseDeltaType):
    """Wrapper for converting objects of one data type into raw bits.

    Note that :meth:`pack` and :meth:`unpack` assume that the value
    has already been converted into raw bits. Use :meth:`as_bits`
    to ensure this is the case when returning this type from a Python node,
    and :meth:`from_bits` when receiving this type as input to a Python node
    to guarantee you get the value rather than its raw binary representation.

    Attributes
    ----------
    base_type : BaseDeltaType
        The data type we are converting to bits.
    """

    def __init__(self, base_type: typing.Union[typing.Type, BaseDeltaType]):
        self.base_type = as_delta_type(base_type)
        if self.base_type == Top():
            raise DeltaTypeError("Raw cannot contain Top.")

    def __eq__(self, other):
        if type(other) is Raw:
            return self.base_type == other.base_type
        else:
            return False

    def __hash__(self):
        return hash(self.base_type)

    def __getattr__(self, item):
        return getattr(self.base_type, item)

    def __str__(self):
        return f"Raw({str(self.base_type)})"

    def as_numpy_object(self, val):
        return self.base_type.as_numpy_object(val)

    def from_numpy_object(self, val):
        return self.base_type.from_numpy_object(val)

    def as_numpy_type(self):
        return self.base_type.as_numpy_type()

    def as_python_type(self):
        return self.base_type.as_python_type()

    def is_packable(self, val):
        return isinstance(val, int)

    def set_pack_format(self):
        self.base_type.set_pack_format()

    def pack(self, val):
        if not self.is_packable(val):
            raise DeltaTypeError(
                "Raw.pack requires int input. Use Raw.as_bits before pack.")
        return format(val, f"0{self.size.val}b").encode("ascii")

    def unpack(self, buffer):
        return int(buffer, 2)

    def as_bits(self, val: BaseDeltaType) -> int:
        """Converts a given value into an integer containing its binary
        representation. This is done using the base type's
        :py:meth:`pack<deltalanguage.data_types.BaseDeltaType.pack>` method.

        Parameters
        ----------
        val : BaseDeltaType
            The value to convert to bits

        Returns
        -------
        int
            The binary representation of val
        """
        return self.unpack(self.base_type.pack(val))

    def from_bits(self, bits: int) -> BaseDeltaType:
        """Converts a bit sequence back to the object those bits represent.
        This is done using the base type's
        :py:meth:`unpack<deltalanguage.data_types.BaseDeltaType.unpack>` method.

        Parameters
        ----------
        bits : int
            The binary representation of the value

        Returns
        -------
        BaseDeltaType
            The original description of the value.
        """
        return self.base_type.unpack(self.pack(bits))


class Optional:
    """Wrapper class that is used to identify optional input for nodes.

    .. note::
        Only :py:class:`InPort<deltalanguage.wiring.InPort>` can be optional.
        :py:class:`OutPort<deltalanguage.wiring.OutPort>` does not have such
        property.

    Examples
    --------
    Create a node with 1 compulsory and 1 optional inputs:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> @dl.DeltaBlock()
        ... def foo(a: int, b: dl.Optional(int)) -> int:
        ...     if b is None:
        ...         return a
        ...     else:
        ...         return a + b

    As usual this function can be used as a normal python function:

    .. code-block:: python

        >>> foo(5, None)
        5

        >>> foo(5, 6)
        11

    Now let's see how it works in the context of
    :py:class:`DeltaGraph<deltalanguage.wiring.DeltaGraph>`:

    .. code-block:: python

        >>> @dl.DeltaBlock()
        ... def bar() -> int:
        ...     # this node will imitate an absence of input
        ...     pass

        # helper node that saves the result
        >>> s = dl.lib.StateSaver(int, verbose=True)

        >>> with dl.DeltaGraph() as graph:
        ...     foo_out = foo(42, bar())
        ...     s.save_and_exit(foo_out)

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 42

    So we can see that the node runs even the optional input is not provided.
    """

    def __init__(self, t: typing.Union[typing.Type, BaseDeltaType]):
        self.type = as_delta_type(t)

    def __eq__(self, other):
        return isinstance(other, Optional) and self.type == other.type

    def __hash__(self):
        return self.type.__hash__() + 1

    @staticmethod
    def as_python_type():
        raise DeltaTypeError('Optional is not a data type')


def is_primitive(t: BaseDeltaType) -> bool:
    return isinstance(t, PrimitiveDeltaType)


def as_delta_type(t: typing.Type) -> typing.Union[BaseDeltaType, Optional]:
    """Map a generic python type to the corresponding Deltaflow type.

    Parameters
    ----------
    t : typing.Type
        Python data type.

    Returns
    -------
    typing.Union[BaseDeltaType, Optional]
        Instance of :py:class:`BaseDeltaType` subclass representing the
        Deltaflow type mapped to the provided Python type.


    .. note::
        Due to restrictions of python typing (python built-in types as
        well as types from ``typing`` library are quite restrictive)
        compound objects need to be analysed using
        :py:func:`delta_type`.


    Examples
    --------
    Simply call this function with any supported python type:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> dl.as_delta_type(int)
        Int32

    Any complex or unsupported data type is recognised as an instance of
    singleton :py:class:`Top`:

    .. code-block:: python

        >>> dl.as_delta_type(dict)
        T
    """
    if isinstance(t, (BaseDeltaType, Optional)):
        return t

    elif t is Void:
        return t

    elif t is None or t is type(None):
        raise DeltaTypeError('Please use Void instead.')

    elif t in (bool, np.bool_) or t is np.dtype(np.bool_):
        return Bool()

    elif t is complex:
        return Complex()

    elif t is np.complex64 or t is np.dtype(np.complex64):
        return Complex(Size(64))

    elif t is np.complex128 or t is np.dtype(np.complex128):
        return Complex(Size(128))

    elif t is int:
        return Int(Size(32))

    elif t is np.int8 or t is np.dtype(np.int8):
        return Char()

    elif t is np.int16 or t is np.dtype(np.int16):
        return Int(Size(16))

    elif t is np.int32 or t is np.dtype(np.int32):
        return Int(Size(32))

    elif t is np.int64 or t is np.dtype(np.int64):
        return Int(Size(64))

    elif t is np.uint8 or t is np.dtype(np.uint8):
        return Char()

    elif t is np.uint16 or t is np.dtype(np.uint16):
        return UInt(Size(16))

    elif t is np.uint32 or t is np.dtype(np.uint32):
        return UInt(Size(32))

    elif t is np.uint64 or t is np.dtype(np.uint64):
        return UInt(Size(64))

    elif t is float:
        return Float(Size(32))

    elif t is np.float32 or t is np.dtype(np.float32):
        return Float(Size(32))

    elif t is np.float64 or t is np.dtype(np.float64):
        return Float(Size(64))

    elif t in (str, np.string_):
        return Str()

    elif type(t) is tuple and t[0] is np.string_:
        return Str(Size(t[1]))

    elif attr.has(t):
        return Record(t)

    elif isinstance(t, np.dtype):
        if len(t.fields) == 1:
            return Array(t.fields['f0'][0].base,
                         Size(t.fields['f0'][0].shape[0]))

        elif t.type is np.record:
            t = attr.make_class(t.name, {name: attr.ib(
                type=t.fields[name][0].base) for name in t.names})
            return Record(t)

        else:
            offsets = [f[1] for f in t.fields.values()]
            if offsets == [0 for _ in range(len(t.fields))]:
                return Union([t.fields[name][0].base for name in t.names])
            else:
                return Tuple([t.fields[name][0].base for name in t.names])

    elif t in (tuple, list):
        raise DeltaTypeError(f'Type {t} is too complex, use data_type(obj) '
                             f'instead of as_data_type(type(obj))')

    elif hasattr(t, '__origin__') and t.__origin__ in (tuple, list):
        # via tuple and list
        raise DeltaTypeError(f'Type {t} is too complex, use data_type(obj) '
                             f'instead of as_data_type(type(obj))')

    elif isinstance(t, str):
        # This case enables doctest to use type annotations.
        try:
            actual_t = eval(t)
            return as_delta_type(actual_t)
        except:
            pass

    return Top()


def delta_type(val: object) -> typing.Union[BaseDeltaType, Optional]:
    """Identifies the Deltaflow type of the object.

    In case of a compound type it will recursively investigate its components
    as well.


    Parameters
    ----------
    val: object
        Any python object.

    Returns
    -------
    typing.Union[BaseDeltaType, Optional]
        Deltaflow data type analogue.

    Examples
    --------
    Simply call this function with any supported python object:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> dl.delta_type(42)
        Int32

    More complex items such as tuples are also recognised:

    .. code-block:: python

        >>> dl.delta_type((42, False, 0.73))
        (Int32, Bool, Float32)

    Any objects whose type is not supported defaults to :py:class:`Top`:

    .. code-block:: python

        >>> dl.delta_type({'a': False})
        T
    """

    if val is None:
        raise DeltaTypeError('Please use Void.')

    elif type(val) in (bool,
                       np.bool_,
                       np.dtype(np.bool_),
                       complex,
                       np.complex64,
                       np.complex128,
                       np.dtype(np.complex64),
                       np.dtype(np.complex128),
                       int,
                       np.int8,
                       np.int16,
                       np.int32,
                       np.int64,
                       np.uint8,
                       np.uint16,
                       np.uint32,
                       np.uint64,
                       np.dtype(np.int8),
                       np.dtype(np.int16),
                       np.dtype(np.int32),
                       np.dtype(np.int64),
                       np.dtype(np.uint8),
                       np.dtype(np.uint16),
                       np.dtype(np.uint32),
                       np.dtype(np.uint64),
                       float,
                       np.float32,
                       np.float64,
                       np.dtype(np.float32),
                       np.dtype(np.float64)):
        # => Bool, UInt, Int, Float, Complex
        return as_delta_type(type(val))

    elif type(val) in (str, np.string_):
        if len(val) == 1:
            return Char()
        else:
            return Str(Size(len(val)))

    elif isinstance(val, typing.Tuple):
        sub_types = tuple(delta_type(e) for e in val)
        return Tuple(sub_types)

    elif isinstance(val, typing.List):
        sub_types = tuple(delta_type(e) for e in val)
        if sub_types[1:] == sub_types[:-1]:
            return Array(sub_types[0], Size(len(sub_types)))
        else:
            raise DeltaTypeError(f'Please provide an array, i.e. a list with '
                                 f'same type elements, {sub_types=}')

    elif isinstance(val, np.ndarray):
        # NumPy transformations
        if len(val.dtype) == 0:
            return Array(val.dtype, Size(val.shape[0]))

        elif val.dtype.type is np.record:
            t = attr.make_class(val.dtype.name, {name: attr.ib(
                type=val.dtype.fields[name][0]) for name in val.dtype.names})
            return Record(t)

        else:
            offsets = [f[1] for f in val.dtype.fields.values()]
            if offsets == [0 for _ in range(len(val.dtype))]:
                return Union([f[0] for f in val.dtype.fields.values()])
            else:
                return Tuple([f[0] for f in val.dtype.fields.values()])

    # => Top
    return as_delta_type(type(val))
