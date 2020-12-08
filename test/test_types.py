"""Characterization test BaseDeltaType and its subclasses."""

import random
from typing import Any, List, Tuple, Union
import unittest

import attr
import numpy as np

from test._utils import TwoIntsT

from deltalanguage._utils import NamespacedName
from deltalanguage.data_types import (
    BaseDeltaType,
    DeltaTypeError,
    DArray,
    DBool,
    DChar,
    DComplex,
    DFloat,
    DInt,
    DRaw,
    DRecord,
    DSize,
    DStr,
    DTuple,
    DUInt,
    DUnion,
    ForkedReturn,
    NoMessage,
    Top,
    as_delta_type,
    delta_type
)
from deltalanguage.wiring import DeltaGraph


@attr.s(slots=True)
class RecBI:

    x: bool = attr.ib()
    y: int = attr.ib()


@attr.s(slots=True)
class RecBI_copy:

    x: bool = attr.ib()
    y: int = attr.ib()


@attr.s(slots=True)
class RecBDi:

    x: bool = attr.ib()
    y: DInt() = attr.ib()


@attr.s(slots=True)
class RecBT:

    x: bool = attr.ib()
    y: Top() = attr.ib()


@attr.s(slots=True)
class RecIB:

    x: int = attr.ib()
    x: bool = attr.ib()


@attr.s(slots=True)
class RecBIS:

    x: bool = attr.ib()
    y: int = attr.ib()
    z: str = attr.ib()


@attr.s(slots=True)
class RecBII:

    x: bool = attr.ib()
    y: int = attr.ib()
    z: int = attr.ib()


@attr.s(slots=True)
class RecIT:

    x: float = attr.ib()
    y: DTuple([int, int]) = attr.ib()


@attr.s(slots=True)
class RecATI:

    x: DArray(int, DSize(2)) = attr.ib()
    y: DTuple([float, int]) = attr.ib()
    z: int = attr.ib()


class DeltaTypesTest(unittest.TestCase):
    """The most basic tests of BaseDeltaType outside of the context of
    wires (streams, channels) and DeltaGraph.
    """

    def test_DSize(self):
        """Test various use DSize."""
        with self.assertRaises(DeltaTypeError):
            DInt(5)

        with self.assertRaises(ValueError):
            DSize(-1)

        with self.assertRaises(ValueError):
            dummy = DSize(4) + DSize(NamespacedName("a", "b"))

        # add
        d16_32 = DSize(16)
        d16_32 += DSize(32)
        self.assertEqual(d16_32, DSize(48))
        self.assertEqual(DSize(4) + DSize(5), DSize(9))

        # sub
        d32_16 = DSize(32)
        d32_16 -= DSize(16)
        self.assertEqual(d32_16, DSize(16))
        self.assertEqual(DSize(5) - DSize(2), DSize(3))
        with self.assertRaises(ValueError):
            dummy = DSize(5) - DSize(6)

        # mul
        self.assertEqual(DSize(4) * 5, DSize(20))
        self.assertEqual(5 * DSize(4), DSize(20))
        d16x4 = DSize(16)
        d16x4 *= 4
        self.assertEqual(d16x4, DSize(64))
        d16x4 = DSize(16)
        d16x4 *= DSize(4)
        self.assertEqual(d16x4, DSize(64))

        # comparison
        self.assertTrue(DSize(8) == DSize(8))
        self.assertTrue(DSize(8) > DSize(6))
        self.assertTrue(DSize(4) < DSize(6))

    def test_size(self):
        """Test how many bits each data type takes."""
        # primitive
        self.assertEqual(DInt().size, DSize(32))
        self.assertEqual(DUInt().size, DSize(32))
        self.assertEqual(DBool().size, DSize(1))
        self.assertEqual(DChar().size, DSize(8))
        self.assertEqual(DFloat().size, DSize(32))

        # compound
        self.assertEqual(DTuple([int, bool]).size, DSize(33))
        self.assertEqual(DArray(int, DSize(10)).size, DSize(320))
        self.assertEqual(DStr().size, DSize(8192))
        self.assertEqual(DRecord(RecBI).size, DSize(33))

        # compound: DUnion
        self.assertEqual(DUnion([bool]).size, DSize(9))
        self.assertEqual(DUnion([int, bool]).size, DSize(40))
        self.assertEqual(DUnion([int, DTuple([int, int])]).size, DSize(2*32+8))

    def test_str(self):
        """Test string representation of data types."""
        # primitive
        self.assertEqual(str(DInt()), "DInt32")
        self.assertEqual(str(DInt(DSize(64))), "DInt64")
        self.assertEqual(str(DUInt()), "DUInt32")
        self.assertEqual(str(DUInt(DSize(64))), "DUInt64")
        self.assertEqual(str(DBool()), "DBool")
        self.assertEqual(str(DChar()), "DChar8")
        self.assertEqual(str(DFloat()), "DFloat32")
        self.assertEqual(str(DFloat(DSize(64))), "DFloat64")

        # compound
        self.assertEqual(str(DArray(int, DSize(8))), "[DInt32 x 8]")
        self.assertEqual(str(DStr()), "DStr8192")
        self.assertEqual(str(DStr(DSize(100))), "DStr800")
        self.assertEqual(str(DTuple([int, bool])), "(DInt32, DBool)")
        self.assertEqual(str(DRecord(RecBIS)),
                         "{x: DBool, y: DInt32, z: DStr8192}")
        self.assertEqual(str(DUnion([int, bool])), "<DBool | DInt32>")

        # compound: DUnion
        self.assertEqual(str(DUnion([int])), "<DInt32>")
        self.assertEqual(str(DUnion([int, DUnion([int, bool])])),
                         "<DBool | DInt32>")
        self.assertEqual(str(DUnion([int, DUnion([int, DUnion([int, bool])])])),
                         "<DBool | DInt32>")

        # incapculation of various types
        self.assertEqual(str(DUnion([int, DTuple([int, bool])])),
                         "<(DInt32, DBool) | DInt32>")
        self.assertEqual(str(DArray(DTuple([int, bool]), DSize(8))),
                         "[(DInt32, DBool) x 8]")

        # special
        self.assertEqual(str(Top()), "T")
        self.assertEqual(str(DSize(5)), "5")
        self.assertEqual(str(DSize(NamespacedName("a", "b"))), "(a.b)")
        self.assertEqual(str(ForkedReturn(dict(x=int, y=bool, z=str))),
                         "ForkedReturn(x:DInt32, y:DBool, z:DStr8192)")

    def test_as_python_type(self):
        """Test conversion of Deltaflow data types to python."""
        # special
        self.assertEqual(Top().as_python_type(), Any)

        # primitive
        self.assertEqual(DInt(DSize(32)).as_python_type(), int)
        self.assertEqual(DInt(DSize(64)).as_python_type(), int)
        self.assertEqual(DUInt(DSize(32)).as_python_type(), int)
        self.assertEqual(DUInt(DSize(64)).as_python_type(), int)
        self.assertEqual(DBool().as_python_type(), bool)
        with self.assertRaises(NotImplementedError):
            DChar().as_python_type()
        self.assertEqual(DFloat(DSize(32)).as_python_type(), float)
        self.assertEqual(DFloat(DSize(64)).as_python_type(), float)
        self.assertEqual(DComplex(DSize(64)).as_python_type(), complex)
        self.assertEqual(DComplex(DSize(128)).as_python_type(), complex)

        # compound
        self.assertEqual(DTuple([int, bool]).as_python_type(),
                         Tuple[int, bool])
        self.assertEqual(DTuple([int, DTuple([int, bool])]).as_python_type(),
                         Tuple[int, Tuple[int, bool]])
        self.assertEqual(DArray(int, DSize(3)).as_python_type(),
                         List[int])

        self.assertEqual(DStr().as_python_type(), str)
        self.assertEqual(DStr(DSize(10)).as_python_type(), str)

        self.assertEqual(DRecord(RecBI).as_python_type(), RecBI)
        self.assertEqual(DRecord(RecBDi).as_python_type(), RecBDi)
        self.assertNotEqual(DRecord(RecBI).as_python_type(), RecBI_copy)

        # compound: DUnion
        self.assertEqual(DUnion([bool, int]).as_python_type(),
                         Union[bool, int])
        self.assertEqual(DUnion([bool, DTuple([int, bool])]).as_python_type(),
                         Union[bool, Tuple[int, bool]])

    def test_types_comparison(self):
        """Various tests of types comparison."""
        # primitive
        self.assertEqual(DInt(DSize(32)), DInt())
        self.assertNotEqual(DInt(), DUInt())
        self.assertNotEqual(DInt(), DInt(DSize(64)))

        # compound
        self.assertEqual(DTuple([int, bool]), DTuple([int, bool]))
        self.assertNotEqual(DTuple([int, bool]), DTuple([bool, int]))
        self.assertEqual(DArray(int, DSize(4)), DArray(int, DSize(4)))
        self.assertEqual(DArray(int, DSize(4)), DArray(DInt(), DSize(4)))
        self.assertNotEqual(DArray(int, DSize(4)), DArray(int, DSize(5)))
        self.assertNotEqual(DStr(), DStr(DSize(100)))
        self.assertEqual(DRecord(RecBI), DRecord(RecBI))

        # compound: DUnion
        self.assertEqual(DUnion([int, bool]), DUnion([bool, int]))
        self.assertEqual(DUnion([int, DUnion([int, bool])]),
                         DUnion([int, bool]))
        self.assertEqual(DUnion([int, DUnion([int, DUnion([int, bool])])]),
                         DUnion([int, bool]))
        self.assertEqual(DUnion([int, int]), DUnion([int]))
        self.assertNotEqual(DUnion([DInt()]), DInt())

        # special
        self.assertEqual(ForkedReturn(dict(x=int, y=bool, z=str)),
                         ForkedReturn(dict(x=int, y=bool, z=str)))

    def test_DUnion(self):
        """DUnion specific types."""

        with self.assertRaises(DeltaTypeError):
            DUnion([])

        with self.assertRaises(DeltaTypeError):
            DUnion([None])

        with self.assertRaises(DeltaTypeError):
            DUnion([None, int])


class DeltaTypesPackTest(unittest.TestCase):
    """Test pack/unpack methods for `BaseDeltaType`."""

    def pack_unpack(self, val, t1, t2=None):
        """Helper that pack and unpack a value via given types."""
        if t2 is None:
            t2 = t1
        buf = t1.pack(val)
        val_new = t2.unpack(buf)
        return val_new

    def check(self, val, t1, t2=None):
        """Test that pack-unpack returns exactly the same message."""
        val_new = self.pack_unpack(val, t1, t2)
        self.assertEqual(val, val_new)

    def check_numpy(self, val, t1):
        val_new = self.pack_unpack(t1.as_numpy_object(val), t1)
        self.assertEqual(val, val_new)

    def check_float(self, val, t: DFloat):
        """Test pack-unpack for floats."""
        if not isinstance(t, DFloat):
            raise DeltaTypeError

        # TODO this check can be done on binary, then the number of places
        # will be more reasonably explained
        if t.size == DSize(32):
            places = 7
        elif t.size == DSize(64):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.pack_unpack(val, t)
        self.assertAlmostEqual(val, val_new, places=places)

    def check_complex(self, val, t: DComplex):
        """Test pack-unpack for complex numbers."""
        if not isinstance(t, DComplex):
            raise DeltaTypeError

        # Using the same idea as check_float, but for real and imaginary parts
        if t.size == DSize(64):
            places = 7
        elif t.size == DSize(128):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.pack_unpack(val, t)
        self.assertAlmostEqual(val.real, val_new.real, places=places)
        self.assertAlmostEqual(val.imag, val_new.imag, places=places)

    def test_DInt(self):
        """Only 8, 32 and 64 bits are supported."""
        self.check(-2**7, DInt(DSize(8)))
        self.check(2**7-1, DInt(DSize(8)))
        for _ in range(1000):
            self.check(random.randint(-2**7, 2**7-1), DInt(DSize(8)))

        self.check(-2**31, DInt(DSize(32)))
        self.check(2**31-1, DInt(DSize(32)))
        for _ in range(1000):
            self.check(random.randint(-2**31, 2**31-1), DInt(DSize(32)))

        self.check(-2**63, DInt(DSize(64)))
        self.check(2**63-1, DInt(DSize(64)))
        for _ in range(1000):
            self.check(random.randint(-2**63, 2**63-1), DInt(DSize(64)))

    def test_DUInt(self):
        """Only 8, 32 and 64 bits are supported."""
        self.check(0, DUInt(DSize(8)))
        self.check(2**7-1, DUInt(DSize(8)))
        for _ in range(1000):
            self.check(random.randint(0, 2**7-1), DUInt(DSize(8)))

        self.check(0, DUInt(DSize(32)))
        self.check(2**32-1, DUInt(DSize(32)))
        for _ in range(1000):
            self.check(random.randint(0, 2**32-1), DUInt(DSize(32)))

        self.check(0, DUInt(DSize(64)))
        self.check(2**64-1, DUInt(DSize(64)))
        for _ in range(1000):
            self.check(random.randint(0, 2**64-1), DUInt(DSize(64)))

    def test_DBool(self):
        self.check(False, DBool())
        self.check(0, DBool())
        self.check(True, DBool())
        self.check(1, DBool())

    def test_DFloat(self):
        for _ in range(1000):
            self.check_float(random.uniform(-1, 1), DFloat(DSize(32)))

        for _ in range(1000):
            self.check_float(random.uniform(-1, 1), DFloat(DSize(64)))

        self.check(1 + 2**-23, DFloat(DSize(32)))
        self.check(1 + 2**-52, DFloat(DSize(64)))

    def test_DComplex(self):
        for _ in range(1000):
            self.check_complex(random.uniform(-1, 1) +
                               random.uniform(-1, 1) * 1j, DComplex(DSize(64)))

        for _ in range(1000):
            self.check_complex(random.uniform(-1, 1) +
                               random.uniform(-1, 1) * 1j, DComplex(DSize(128)))

    def test_DArray(self):
        # primitive elements are poperly handled
        # int are passed as DInt, not DUInt
        self.check([1, 2, 3], DArray(DInt(), DSize(3)))
        with self.assertRaises(DeltaTypeError):
            self.check([1, 2, 3], DArray(DUInt(), DSize(3)))

        # for floats use a dot
        # might be a potential problem, due to python silent type downcasting
        self.check([1.0, 2.0, 3.0], DArray(DFloat(), DSize(3)))
        with self.assertRaises(DeltaTypeError):
            self.check([1, 2, 3], DArray(DFloat(), DSize(3)))

        # bool are passed as DBool, not DInt
        self.check([True, False, False], DArray(DBool(), DSize(3)))
        with self.assertRaises(DeltaTypeError):
            self.check([1, 0, 0], DArray(DBool(), DSize(3)))

        # incapsulation
        self.check([[1, 2, 3], [4, 5, 6]],
                   DArray(DArray(DInt(), DSize(3)), DSize(2)))

        with self.assertRaises(DeltaTypeError):
            self.check([1, 2, 3, 4, 5, 6],
                       DArray(DArray(DInt(), DSize(3)), DSize(2)))

        with self.assertRaises(AssertionError):
            self.check([1, 2, 3, 4, 5, 6],
                       DArray(DInt(), DSize(6)),
                       DArray(DArray(DInt(), DSize(3)), DSize(2)))

        # mixed types
        self.check([(1, 2, 3), (4, 5, 6)],
                   DArray(DTuple([int, int, int]), DSize(2)))

        self.check(["hello", "world"], DArray(DStr(DSize(5)), DSize(2)))
        # numpy
        self.check_numpy([1, 2, 3, 4, 5], DArray(int, DSize(5)))

    def test_DStr(self):
        self.check('hello world', DStr())
        self.check('A' * 1024, DStr())
        self.check('check digits 14213', DStr())
        self.check('check spaces in the end ', DStr())

        with self.assertRaises(DeltaTypeError):
            self.check('123456', DStr(DSize(4)))

        self.check((-5, 'text'), DTuple([int, DStr()]))
        self.check(['hello', 'world!'], DArray(DStr(), DSize(2)))

        self.check_numpy('hello world', DStr())

    def test_DTuple(self):
        # primitive elements are poperly handled
        self.check((-5, True, 3.25), DTuple([int, bool, float]))

        with self.assertRaises(DeltaTypeError):
            self.check((-5, True, 3.25), DTuple([int, bool, int]))

        # incapsulation
        self.check((-5, (1, 2)), DTuple([int, DTuple([int, int])]))

        with self.assertRaises(AssertionError):
            self.check((-5, (1, 2)),
                       DTuple([int, DTuple([int, int])]),
                       DTuple([int, int, int]))

        # mixed types
        self.check(([1, 2, 3], [4.0, 5.0]),
                   DTuple([DArray(int, DSize(3)), DArray(float, DSize(2))]))

        self.check(("hello", "world"), DTuple([DStr(), DStr(DSize(6))]))
        self.check_numpy((1, 2.0, True), DTuple([int, float, bool]))

    def test_DRecord(self):
        # primitive
        self.check(RecBI(True, 5), DRecord(RecBI))
        self.check(-4, DInt())
        self.check(RecBII(True, 5, -4), DRecord(RecBII))
        with self.assertRaises(DeltaTypeError):
            self.check(RecBI(True, 5), DRecord(RecIB))

        # mixed
        self.check(RecIT(-4.0, (1, 2)), DRecord(RecIT))
        self.check(RecATI([1, 2], (3.0, 4), 5),
                   DRecord(RecATI))

        self.check((RecIT(-4.0, (1, 2)), 1),
                   DTuple([DRecord(RecIT), int]))

        self.check([RecIT(-4.0, (1, 2)), RecIT(5.0, (-3, -4))],
                   DArray(DRecord(RecIT), DSize(2)))

        # numpy
        self.check_numpy(RecBI(False, 2), DRecord(RecBI))

    def test_DUnion(self):
        # primitive
        self.check(5, DUnion([int, bool]), DUnion([int, bool]))
        self.check(True, DUnion([int, bool]), DUnion([bool, int]))

        # compound
        self.check(5, DUnion([int, DTuple([int, float])]))
        self.check((4, 5), DUnion([int, DTuple([int, int])]))
        self.check((4, 5),
                   DUnion([DArray(int, DSize(2)), DTuple([int, int])]))
        self.check([4, 5],
                   DUnion([DArray(int, DSize(2)), DTuple([int, int])]))

        # buffer's size is always the same
        self.assertEqual(len(DUnion([int, bool]).pack(5)),
                         DUnion([int, bool]).size.val)
        self.assertEqual(len(DUnion([int, bool]).pack(True)),
                         DUnion([int, bool]).size.val)

        # numpy (throws error)
        with self.assertRaises(
                DeltaTypeError,
                msg="NumPy unions cannot be converted to Python types."):
            self.check_numpy(5, DUnion([bool, float, int]))


class WiresTest(unittest.TestCase):
    """Testing the rules of data transmission in a sinlge wire of DeltaGraph."""

    def test_primitive_types(self):
        """Strict typing without subtyping."""
        self.assertTrue(DeltaGraph.check_wire(DInt(), DInt()))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DInt(), DUInt())

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DUInt(), DInt())

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(int, int)

    def test_Top(self):
        """Everything can be accepted as Top()."""
        self.assertTrue(DeltaGraph.check_wire(DInt(), Top()))
        self.assertTrue(DeltaGraph.check_wire(DUInt(), Top()))
        self.assertTrue(DeltaGraph.check_wire(DBool(), Top()))
        self.assertTrue(DeltaGraph.check_wire(DTuple([int, bool]), Top()))
        self.assertTrue(DeltaGraph.check_wire(DUnion([int, bool]), Top()))
        self.assertTrue(DeltaGraph.check_wire(DArray(int, DSize(8)), Top()))
        self.assertTrue(DeltaGraph.check_wire(DStr(), Top()))
        self.assertTrue(DeltaGraph.check_wire(DRecord(RecBI), Top()))
        self.assertTrue(DeltaGraph.check_wire(Top(), Top()))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Top(), DInt())

        # however it's not true if Top is used within a non-primitive type
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DTuple([int, int]), DTuple([int, Top()]))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DArray(int, DSize(8)),
                                  DArray(Top(), DSize(8)))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DRecord(RecBI), DRecord(RecBT))

    def test_DUnion(self):
        """Test wires with DUnion."""
        # examples of obvious behaiviour
        self.assertTrue(DeltaGraph.check_wire(DUnion([int, bool]),
                                              DUnion([int, bool])))
        self.assertTrue(DeltaGraph.check_wire(DUnion([int, bool]),
                                              DUnion([bool, int])))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DUnion([int, bool]), DInt())
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DUnion([int, bool, float]),
                                  DUnion([int, bool]))

        # strict typing even with DUnion, i.e. all subtypes should match
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DUnion([bool, int]),
                                  DUnion([bool, int, float]))

        # DUnion changes packing method, thus these tests should fail
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DInt(), DUnion([int]))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DUnion([int]), DInt())

    def test_DArray(self):
        """Only strict typing."""
        self.assertTrue(DeltaGraph.check_wire(DArray(int, DSize(8)),
                                              DArray(int, DSize(8))))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DArray(int, DSize(10)),
                                  DArray(int, DSize(8)))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DArray(int, DSize(8)),
                                  DArray(int, DSize(10)))

    def test_DTuple(self):
        """Only strict typing."""
        self.assertTrue(DeltaGraph.check_wire(DTuple([int, bool]),
                                              DTuple([int, bool])))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DTuple([int, bool]),
                                  DTuple([bool, int]))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DTuple([int, bool]),
                                  DTuple([int, bool, bool]))

    def test_DRecord(self):
        """Only strict typing."""
        self.assertTrue(DeltaGraph.check_wire(DRecord(RecBI), DRecord(RecBI)))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DRecord(RecBI), DRecord(RecIB))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DRecord(RecBIS), DRecord(RecBI))

    def test_ForkedReturn(self):
        self.assertTrue(DeltaGraph.check_wire(TwoIntsT.elem_dict['x'],
                                              DInt()))


class UtilsTest(unittest.TestCase):
    """Helper funtions."""

    def test_as_delta_type(self):
        """Test conversion from python to Deltaflow data types."""
        # special
        self.assertEqual(as_delta_type(object), Top())
        self.assertEqual(as_delta_type(type(object)), Top())
        self.assertEqual(as_delta_type(type), Top())

        self.assertEqual(as_delta_type(NoMessage), NoMessage)

        with self.assertRaises(DeltaTypeError):
            as_delta_type(None)
        with self.assertRaises(DeltaTypeError):
            as_delta_type(type(None))

        # primitive
        self.assertNotEqual(as_delta_type(bool), DUInt(DSize(1)))
        self.assertEqual(as_delta_type(bool), DBool())
        self.assertEqual(as_delta_type(np.bool_), DBool())
        self.assertEqual(as_delta_type(int), DInt(DSize(32)))
        self.assertEqual(as_delta_type(np.int8), DChar())
        self.assertEqual(as_delta_type(np.int16), DInt(DSize(16)))
        self.assertEqual(as_delta_type(np.int32), DInt(DSize(32)))
        self.assertEqual(as_delta_type(np.int64), DInt(DSize(64)))
        self.assertEqual(as_delta_type(np.uint8), DChar())
        self.assertEqual(as_delta_type(np.uint16), DUInt(DSize(16)))
        self.assertEqual(as_delta_type(np.uint32), DUInt(DSize(32)))
        self.assertEqual(as_delta_type(np.uint64), DUInt(DSize(64)))
        self.assertEqual(as_delta_type(float), DFloat())
        self.assertEqual(as_delta_type(np.float32), DFloat(DSize(32)))
        self.assertEqual(as_delta_type(np.float64), DFloat(DSize(64)))
        self.assertEqual(as_delta_type(complex), DComplex())
        self.assertEqual(as_delta_type(np.complex64), DComplex(DSize(64)))
        self.assertEqual(as_delta_type(np.complex128), DComplex(DSize(128)))

        # compound
        with self.assertRaises(DeltaTypeError):
            as_delta_type(Tuple[int, bool])
        with self.assertRaises(DeltaTypeError):
            as_delta_type(List[int])
        self.assertNotEqual(as_delta_type(str), DArray(DChar(), DSize(1024)))
        self.assertEqual(as_delta_type(str), DStr())
        self.assertEqual(as_delta_type(RecBI), DRecord(RecBI))

        # numpy compound
        self.assertEqual(as_delta_type(DArray(int, DSize(5)).as_numpy_type()),
                         DArray(int, DSize(5)))
        self.assertEqual(as_delta_type(DStr().as_numpy_type()), DStr())
        self.assertEqual(
            as_delta_type(DTuple([int, bool, float]).as_numpy_type()),
            DTuple([int, bool, float]))
        self.assertEqual(as_delta_type(DRecord(RecBI).as_numpy_type()),
                         DRecord(RecBI))
        self.assertEqual(
            as_delta_type(DUnion([bool, float, int]).as_numpy_type()),
            DUnion([bool, float, int]))

    def test_delta_type(self):
        """Redundant tests."""
        # primitive
        with self.assertRaises(DeltaTypeError):
            delta_type(None)
        self.assertEqual(delta_type(False), DBool())
        self.assertEqual(delta_type(np.bool_(False)), DBool())
        self.assertEqual(delta_type(5), DInt(DSize(32)))
        self.assertEqual(delta_type(np.int16(5)), DInt(DSize(16)))
        self.assertEqual(delta_type(np.int32(5)), DInt(DSize(32)))
        self.assertEqual(delta_type(np.int64(5)), DInt(DSize(64)))
        self.assertEqual(delta_type(np.uint16(5)), DUInt(DSize(16)))
        self.assertEqual(delta_type(np.uint32(5)), DUInt(DSize(32)))
        self.assertEqual(delta_type(np.uint64(5)), DUInt(DSize(64)))
        self.assertEqual(delta_type(4.2), DFloat(DSize(32)))
        self.assertEqual(delta_type(np.float32(4.2)), DFloat(DSize(32)))
        self.assertEqual(delta_type(np.float64(4.2)), DFloat(DSize(64)))
        self.assertEqual(delta_type(3+1j), DComplex(DSize(64)))
        self.assertEqual(delta_type(np.complex64(3+1j)), DComplex(DSize(64)))
        self.assertEqual(delta_type(np.complex128(3+1j)), DComplex(DSize(128)))
        self.assertEqual(delta_type('c'), DChar())

        # compound
        self.assertEqual(delta_type((1, True, 3.7)),
                         DTuple([int, bool, float]))
        self.assertEqual(delta_type([1, 2, 4]), DArray(int, DSize(3)))
        self.assertEqual(delta_type(RecBI(True, 5)), DRecord(RecBI))

        # numpy compound
        self.assertEqual(delta_type(np.array([1, 2, 3, 4, 5])),
                         DArray(DInt(DSize(64)), DSize(5)))
        self.assertEqual(delta_type(
            DStr(DSize(5)).as_numpy_object("abcde")), DStr(DSize(5)))
        self.assertEqual(
            delta_type(DTuple([int, float, bool]
                              ).as_numpy_object((1, 2.0, True))),
            DTuple([int, float, bool]))
        self.assertEqual(
            delta_type(DRecord(RecBI).as_numpy_object(RecBI(True, 2))),
            DRecord(RecBI))
        self.assertEqual(
            delta_type(DUnion([bool, float, int]).as_numpy_object(5.0)),
            DUnion([bool, float, int]))

        # different combinations
        self.assertEqual(delta_type([(4, 4.3), (2, 3.3)]),
                         DArray(DTuple([int, float]), DSize(2)))


class DeltaTypesNumpyTest(unittest.TestCase):

    def to_np_and_back(self, val, t):
        return t.from_numpy_object(t.as_numpy_object(val))

    def check(self, val, t):
        self.assertEqual(self.to_np_and_back(val, t), val)

    def check_float(self, val, t: DFloat):
        """Test pack-unpack for floats."""
        if not isinstance(t, DFloat):
            raise DeltaTypeError

        # TODO this check can be done on binary, then the number of places
        # will be more reasonably explained
        if t.size == DSize(32):
            places = 6
        elif t.size == DSize(64):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.to_np_and_back(val, t)
        self.assertAlmostEqual(val, val_new, places=places)

    def check_complex(self, val, t: DComplex):
        """Test pack-unpack for complex numbers."""
        if not isinstance(t, DComplex):
            raise DeltaTypeError

        # Using the same idea as check_float, but for real and imaginary parts
        if t.size == DSize(64):
            places = 6
        elif t.size == DSize(128):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.to_np_and_back(val, t)
        self.assertAlmostEqual(val.real, val_new.real, places=places)
        self.assertAlmostEqual(val.imag, val_new.imag, places=places)

    def test_Top(self):
        with self.assertRaises(NotImplementedError):
            Top().as_numpy_type()

        with self.assertRaises(NotImplementedError):
            Top().as_numpy_object(True)

        with self.assertRaises(NotImplementedError):
            Top().from_numpy_object(np.bool_(False))

    def test_DBool(self):
        self.assertEqual(DBool().as_numpy_type(), np.bool_)

    def test_DBool_object(self):
        self.check(False, DBool())

    def test_DInt_type(self):
        self.assertEqual(DInt(DSize(8)).as_numpy_type(), np.int8)
        self.assertEqual(DInt(DSize(16)).as_numpy_type(), np.int16)
        self.assertEqual(DInt(DSize(32)).as_numpy_type(), np.int32)
        self.assertEqual(DInt(DSize(64)).as_numpy_type(), np.int64)
        with self.assertRaises(NotImplementedError):
            DInt(DSize(128)).as_numpy_type()

    def test_DInt_object(self):
        self.check(5, DInt(DSize(8)))
        self.check(10, DInt(DSize(16)))
        self.check(15, DInt(DSize(32)))
        self.check(20, DInt(DSize(64)))

    def test_DUInt_type(self):
        self.assertEqual(DUInt(DSize(8)).as_numpy_type(), np.uint8)
        self.assertEqual(DUInt(DSize(16)).as_numpy_type(), np.uint16)
        self.assertEqual(DUInt(DSize(32)).as_numpy_type(), np.uint32)
        self.assertEqual(DUInt(DSize(64)).as_numpy_type(), np.uint64)
        with self.assertRaises(NotImplementedError):
            DUInt(DSize(128)).as_numpy_type()

    def test_DUInt_object(self):
        self.check(5, DUInt(DSize(8)))
        self.check(10, DUInt(DSize(16)))
        self.check(15, DUInt(DSize(32)))
        self.check(20, DUInt(DSize(64)))

    def test_DChar_type(self):
        self.assertEqual(DChar().as_numpy_type(), np.uint8)

    def test_DChar_object(self):
        self.check('a', DChar())

    def test_DFloat_type(self):
        self.assertEqual(DFloat(DSize(32)).as_numpy_type(), np.float32)
        self.assertEqual(DFloat(DSize(64)).as_numpy_type(), np.float64)
        with self.assertRaises(NotImplementedError):
            DUInt(DSize(128)).as_numpy_type()

    def test_DFloat_object(self):
        self.check_float(3.14, DFloat(DSize(32)))
        self.check_float(6.28, DFloat(DSize(64)))

    def test_DComplex_type(self):
        self.assertEqual(DComplex(DSize(64)).as_numpy_type(), np.complex64)
        self.assertEqual(DComplex(DSize(128)).as_numpy_type(), np.complex128)

    def test_DComplex_object(self):
        self.check_complex(1 + 0.5j, DComplex(DSize(64)))
        self.check_complex(5 + 0.2j, DComplex(DSize(128)))

    def test_DArray_type(self):
        int_type = DArray(int, DSize(5)).as_numpy_type()
        self.assertEqual(int_type[0], (np.int32, (5,)))

    def test_DArray_object(self):
        self.check([1, 2, 3, 4, 5], DArray(int, DSize(5)))

    def test_DStr_type(self):
        str_type = DStr(DSize(32)).as_numpy_type()
        self.assertEqual(str_type, (np.string_, 32))

    def test_DStr_object(self):
        self.check("abcde", DStr(DSize(32)))

    def test_DTuple_type(self):
        tuple_type = DTuple((int, bool, DChar())).as_numpy_type()
        self.assertEqual(tuple_type[0], np.int32)
        self.assertEqual(tuple_type[1], np.bool_)
        self.assertEqual(tuple_type[2], np.uint8)

    def test_DTuple_object(self):
        t = DTuple((int, bool, DChar()))
        self.check((5, True, 'c'), t)

    def test_DRecord_type(self):
        record_type = DRecord(RecBI).as_numpy_type()
        self.assertEqual(record_type['x'], np.bool_)
        self.assertEqual(record_type['y'], np.int32)

    def test_DRecord_object(self):
        rectangle = RecBI(True, 5)
        self.check(rectangle, DRecord(RecBI))

    def test_DUnion_type(self):
        union_type = DUnion([bool, DChar(), int]).as_numpy_type()
        self.assertEqual(union_type[0], np.bool_)
        self.assertEqual(union_type[1], np.uint8)
        self.assertEqual(union_type[2], np.int32)
        self.assertEqual(union_type.fields['DBool'][1], 0)
        self.assertEqual(union_type.fields['DChar8'][1], 0)
        self.assertEqual(union_type.fields['DInt32'][1], 0)

    def test_DUnion_object(self):
        union_object = DUnion([bool, DChar(), int]).as_numpy_object('c')
        self.assertEqual(union_object[0]["DChar8"], 99)

        with self.assertRaises(
                DeltaTypeError,
                msg="NumPy unions cannot be converted to Python types."):
            self.check('c', DUnion([bool, DChar(), int]))

    def test_compound_objects(self):
        t = DArray(DTuple([bool, int]), DSize(3))
        val = [(True, 1), (False, 2), (True, 3), (False, 4), (True, 5)]
        self.check(val, t)

        t = DTuple([int, DTuple([bool, int])])
        val = (12, (True, 8))
        self.check(val, t)

        t = DTuple([int, DArray(int, DSize(2))])
        val = (12, [14, 18])
        self.check(val, t)

        t = DTuple([int, DStr()])
        val = (12, "hello")
        self.check(val, t)

        t = DTuple([int, DRecord(RecBI)])
        val = (12, RecBI(True, 8))
        self.check(val, t)

        t = DTuple([int, DUnion([bool, int])])
        val = (12, True)
        np_val = t.as_numpy_object(val)
        self.assertEqual(DInt().from_numpy_object(np_val[0][0]), 12)
        self.assertEqual(DBool().from_numpy_object(np_val[0][1][1]), True)

        t = DRecord(RecATI)
        val = RecATI([1, 2], (3.0, 4), 5)
        self.check(val, t)

        t = DUnion([DArray(int, DSize(2)), int])
        val = [1, 2]
        np_val = t.as_numpy_object(val)
        new_val = DArray(int, DSize(2)).from_numpy_object(np_val[0][1])
        self.assertEqual(val, new_val)

        t = DUnion([str, int])
        val = "abcde"
        np_val = t.as_numpy_object(val)
        new_val = DStr().from_numpy_object(np_val[0][1])
        self.assertEqual(val, new_val)


class DRawTest(unittest.TestCase):

    def to_and_from_bits(self, val, base_type):
        """Helper that converts a value to and from bits via given type."""
        raw_type = DRaw(base_type)
        return raw_type.from_bits(raw_type.as_bits(val))

    def pack_unpack(self, val, base_type):
        """Packs and unpacks a DRaw type."""
        raw_type = DRaw(base_type)
        packed = raw_type.pack(raw_type.as_bits(val))
        return raw_type.from_bits(raw_type.unpack(packed))

    def check_error(self, val, base_type):
        if not isinstance(val, int):
            with self.assertRaises(DeltaTypeError):
                DRaw(base_type).pack(val)

    def check(self, val, t):
        """Test that to and from bits returns exactly the same message."""
        val_new = self.to_and_from_bits(val, t)
        self.assertEqual(val, val_new)
        val_new = self.pack_unpack(val, t)
        self.assertEqual(val, val_new)
        self.check_error(val, t)

    def check_float(self, val, t: DFloat):
        """Test for floats."""
        if not isinstance(t, DFloat):
            raise DeltaTypeError

        # TODO this check can be done on binary, then the number of places
        # will be more reasonably explained
        if t.size == DSize(32):
            places = 7
        elif t.size == DSize(64):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.to_and_from_bits(val, t)
        self.assertAlmostEqual(val, val_new, places=places)
        val_new = self.pack_unpack(val, t)
        self.assertAlmostEqual(val, val_new, places=places)
        self.check_error(val, t)

    def check_complex(self, val, t: DComplex):
        """Test for complex numbers."""
        if not isinstance(t, DComplex):
            raise DeltaTypeError

        # Using the same idea as check_float, but for real and imaginary parts
        if t.size == DSize(64):
            places = 7
        elif t.size == DSize(128):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.to_and_from_bits(val, t)
        self.assertAlmostEqual(val.real, val_new.real, places=places)
        self.assertAlmostEqual(val.imag, val_new.imag, places=places)
        val_new = self.pack_unpack(val, t)
        self.assertAlmostEqual(val.real, val_new.real, places=places)
        self.assertAlmostEqual(val.imag, val_new.imag, places=places)
        self.check_error(val, t)

    def test_DInt(self):
        """Only 8, 32 and 64 bits are supported."""
        self.check(-2**7, DInt(DSize(8)))
        self.check(2**7-1, DInt(DSize(8)))
        for _ in range(1000):
            self.check(random.randint(-2**7, 2**7-1), DInt(DSize(8)))

        self.check(-2**31, DInt(DSize(32)))
        self.check(2**31-1, DInt(DSize(32)))
        for _ in range(1000):
            self.check(random.randint(-2**31, 2**31-1), DInt(DSize(32)))

        self.check(-2**63, DInt(DSize(64)))
        self.check(2**63-1, DInt(DSize(64)))
        for _ in range(1000):
            self.check(random.randint(-2**63, 2**63-1), DInt(DSize(64)))

        self.assertTrue(DeltaGraph.check_wire(DRaw(int), DRaw(int)))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DRaw(DInt(DSize(32))),
                                  DRaw(DInt(DSize(64))))

    def test_DUInt(self):
        """Only 8, 32 and 64 bits are supported."""
        self.check(0, DUInt(DSize(8)))
        self.check(2**7-1, DUInt(DSize(8)))
        for _ in range(1000):
            self.check(random.randint(0, 2**7-1), DUInt(DSize(8)))

        self.check(0, DUInt(DSize(32)))
        self.check(2**32-1, DUInt(DSize(32)))
        for _ in range(1000):
            self.check(random.randint(0, 2**32-1), DUInt(DSize(32)))

        self.check(0, DUInt(DSize(64)))
        self.check(2**64-1, DUInt(DSize(64)))
        for _ in range(1000):
            self.check(random.randint(0, 2**64-1), DUInt(DSize(64)))

        self.assertTrue(DeltaGraph.check_wire(DRaw(DUInt(DSize(32))),
                                              DRaw(DUInt(DSize(32)))))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DRaw(DUInt(DSize(32))),
                                  DRaw(DUInt(DSize(64))))

    def test_DBool(self):
        self.check(False, DBool())
        self.check(0, DBool())
        self.check(True, DBool())
        self.check(1, DBool())
        self.assertTrue(DeltaGraph.check_wire(DRaw(DBool()), DRaw(DBool())))

    def test_DFloat(self):
        for _ in range(1000):
            self.check_float(random.uniform(-1, 1), DFloat(DSize(32)))

        for _ in range(1000):
            self.check_float(random.uniform(-1, 1), DFloat(DSize(64)))

        self.check(1 + 2**-23, DFloat(DSize(32)))
        self.check(1 + 2**-52, DFloat(DSize(64)))
        self.assertTrue(DeltaGraph.check_wire(DRaw(float), DRaw(float)))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DRaw(DFloat(DSize(32))),
                                  DRaw(DFloat(DSize(64))))

    def test_DComplex(self):
        for _ in range(1000):
            self.check_complex(random.uniform(-1, 1) +
                               random.uniform(-1, 1) * 1j, DComplex(DSize(64)))

        for _ in range(1000):
            self.check_complex(random.uniform(-1, 1) +
                               random.uniform(-1, 1) * 1j, DComplex(DSize(128)))
        self.assertTrue(DeltaGraph.check_wire(DRaw(complex), DRaw(complex)))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DRaw(DComplex(DSize(64))),
                                  DRaw(DComplex(DSize(128))))

    def test_DArray(self):
        # primitive elements are poperly handled
        # int are passed as DInt, not DUInt
        self.check([1, 2, 3], DArray(DInt(), DSize(3)))

        # for floats use a dot
        # might be a potential problem, due to python silent type downcasting
        self.check([1.0, 2.0, 3.0], DArray(DFloat(), DSize(3)))

        # bool are passed as DBool, not DInt
        self.check([True, False, False], DArray(DBool(), DSize(3)))

        # incapsulation
        self.check([[1, 2, 3], [4, 5, 6]],
                   DArray(DArray(DInt(), DSize(3)), DSize(2)))

        # mixed types
        self.check([(1, 2, 3), (4, 5, 6)],
                   DArray(DTuple([int, int, int]), DSize(2)))

        self.check(["hello", "world"], DArray(DStr(DSize(5)), DSize(2)))
        self.assertTrue(DeltaGraph.check_wire(DRaw(DArray(int, DSize(2))),
                                              DRaw(DArray(int, DSize(2)))))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(DRaw(DArray(int, DSize(2))),
                                  DRaw(DArray(int, DSize(3))))

    def test_DStr(self):
        self.check('hello world', DStr())
        self.check('A' * 1024, DStr())
        self.check('check digits 14213', DStr())
        self.check('check spaces in the end ', DStr())

        self.check((-5, 'text'), DTuple([int, DStr()]))
        self.check(['hello', 'world!'], DArray(DStr(), DSize(2)))
        self.assertTrue(DeltaGraph.check_wire(DRaw(DStr()), DRaw(DStr())))

    def test_DTuple(self):
        # primitive elements are poperly handled
        self.check((-5, True, 3.25), DTuple([int, bool, float]))

        # incapsulation
        self.check((-5, (1, 2)), DTuple([int, DTuple([int, int])]))

        # mixed types
        self.check(([1, 2, 3], [4.0, 5.0]),
                   DTuple([DArray(int, DSize(3)), DArray(float, DSize(2))]))

        self.check(("hello", "world"), DTuple([DStr(), DStr(DSize(6))]))
        self.assertTrue(DeltaGraph.check_wire(DRaw(DTuple([DStr(), int])),
                                              DRaw(DTuple([DStr(), int]))))

    def test_DRecord(self):
        # primitive
        self.check(RecBI(True, 5), DRecord(RecBI))
        self.check(-4, DInt())
        self.check(RecBII(True, 5, -4), DRecord(RecBII))

        # mixed
        self.check(RecIT(-4.0, (1, 2)), DRecord(RecIT))
        self.check(RecATI([1, 2], (3.0, 4), 5),
                   DRecord(RecATI))

        self.check((RecIT(-4.0, (1, 2)), 1),
                   DTuple([DRecord(RecIT), int]))

        self.check([RecIT(-4.0, (1, 2)), RecIT(5.0, (-3, -4))],
                   DArray(DRecord(RecIT), DSize(2)))
        self.assertTrue(DeltaGraph.check_wire(DRaw(DRecord(RecIT)),
                                              DRaw(DRecord(RecIT))))

    def test_DUnion(self):
        # primitive
        self.check(5, DUnion([int, bool]))
        self.check(True, DUnion([int, bool]))

        # compound
        self.check(5, DUnion([int, DTuple([int, float])]))
        self.check((4, 5), DUnion([int, DTuple([int, int])]))
        self.check((4, 5),
                   DUnion([DArray(int, DSize(2)), DTuple([int, int])]))
        self.check([4, 5],
                   DUnion([DArray(int, DSize(2)), DTuple([int, int])]))
        self.assertTrue(DeltaGraph.check_wire(DRaw(DUnion([DStr(), int])),
                                              DRaw(DUnion([DStr(), int]))))


if __name__ == "__main__":
    unittest.main()
