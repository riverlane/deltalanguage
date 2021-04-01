"""Characterization test BaseDeltaType and its subclasses."""

import random
import typing
import unittest

import attr
import numpy as np

from deltalanguage._utils import NamespacedName
from deltalanguage.data_types import (
    BaseDeltaType,
    DeltaTypeError,
    Array,
    Bool,
    Char,
    Complex,
    Float,
    Int,
    Raw,
    Record,
    Size,
    Str,
    Tuple,
    UInt,
    Union,
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
    y: Int() = attr.ib()


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
    y: Tuple([int, int]) = attr.ib()


@attr.s(slots=True)
class RecATI:

    x: Array(int, Size(2)) = attr.ib()
    y: Tuple([float, int]) = attr.ib()
    z: int = attr.ib()


class DeltaTypesTest(unittest.TestCase):
    """The most basic tests of BaseDeltaType outside of the context of
    wires (streams, channels) and DeltaGraph.
    """

    def test_Size(self):
        """Test various use Size."""
        with self.assertRaises(DeltaTypeError):
            Int(5)

        with self.assertRaises(ValueError):
            Size(-1)

        with self.assertRaises(ValueError):
            dummy = Size(4) + Size(NamespacedName("a", "b"))

        # add
        d16_32 = Size(16)
        d16_32 += Size(32)
        self.assertEqual(d16_32, Size(48))
        self.assertEqual(Size(4) + Size(5), Size(9))

        # sub
        d32_16 = Size(32)
        d32_16 -= Size(16)
        self.assertEqual(d32_16, Size(16))
        self.assertEqual(Size(5) - Size(2), Size(3))
        with self.assertRaises(ValueError):
            dummy = Size(5) - Size(6)

        # mul
        self.assertEqual(Size(4) * 5, Size(20))
        self.assertEqual(5 * Size(4), Size(20))
        d16x4 = Size(16)
        d16x4 *= 4
        self.assertEqual(d16x4, Size(64))
        d16x4 = Size(16)
        d16x4 *= Size(4)
        self.assertEqual(d16x4, Size(64))

        # comparison
        self.assertTrue(Size(8) == Size(8))
        self.assertTrue(Size(8) > Size(6))
        self.assertTrue(Size(4) < Size(6))

    def test_size(self):
        """Test how many bits each data type takes."""
        # primitive
        self.assertEqual(Int().size, Size(32))
        self.assertEqual(UInt().size, Size(32))
        self.assertEqual(Bool().size, Size(1))
        self.assertEqual(Char().size, Size(8))
        self.assertEqual(Float().size, Size(32))

        # compound
        self.assertEqual(Tuple([int, bool]).size, Size(33))
        self.assertEqual(Array(int, Size(10)).size, Size(320))
        self.assertEqual(Str().size, Size(8192))
        self.assertEqual(Record(RecBI).size, Size(33))

        # compound: Union
        self.assertEqual(Union([bool]).size, Size(9))
        self.assertEqual(Union([int, bool]).size, Size(40))
        self.assertEqual(Union([int, Tuple([int, int])]).size, Size(2*32+8))

    def test_str(self):
        """Test string representation of data types."""
        # primitive
        self.assertEqual(str(Int()), "Int32")
        self.assertEqual(str(Int(Size(64))), "Int64")
        self.assertEqual(str(UInt()), "UInt32")
        self.assertEqual(str(UInt(Size(64))), "UInt64")
        self.assertEqual(str(Bool()), "Bool")
        self.assertEqual(str(Char()), "Char8")
        self.assertEqual(str(Float()), "Float32")
        self.assertEqual(str(Float(Size(64))), "Float64")

        # compound
        self.assertEqual(str(Array(int, Size(8))), "[Int32 x 8]")
        self.assertEqual(str(Str()), "Str8192")
        self.assertEqual(str(Str(Size(100))), "Str800")
        self.assertEqual(str(Tuple([int, bool])), "(Int32, Bool)")
        self.assertEqual(str(Record(RecBIS)),
                         "{x: Bool, y: Int32, z: Str8192}")
        self.assertEqual(str(Union([int, bool])), "<Bool | Int32>")

        # compound: Union
        self.assertEqual(str(Union([int])), "<Int32>")
        self.assertEqual(str(Union([int, Union([int, bool])])),
                         "<Bool | Int32>")
        self.assertEqual(str(Union([int, Union([int, Union([int, bool])])])),
                         "<Bool | Int32>")

        # encapsulation of various types
        self.assertEqual(str(Union([int, Tuple([int, bool])])),
                         "<(Int32, Bool) | Int32>")
        self.assertEqual(str(Array(Tuple([int, bool]), Size(8))),
                         "[(Int32, Bool) x 8]")

        # special
        self.assertEqual(str(Top()), "T")
        self.assertEqual(str(Size(5)), "5")
        self.assertEqual(str(Size(NamespacedName("a", "b"))), "(a.b)")

    def test_as_python_type(self):
        """Test conversion of Deltaflow data types to python."""
        # special
        self.assertEqual(Top().as_python_type(), typing.Any)

        # primitive
        self.assertEqual(Int(Size(32)).as_python_type(), int)
        self.assertEqual(Int(Size(64)).as_python_type(), int)
        self.assertEqual(UInt(Size(32)).as_python_type(), int)
        self.assertEqual(UInt(Size(64)).as_python_type(), int)
        self.assertEqual(Bool().as_python_type(), bool)
        with self.assertRaises(NotImplementedError):
            Char().as_python_type()
        self.assertEqual(Float(Size(32)).as_python_type(), float)
        self.assertEqual(Float(Size(64)).as_python_type(), float)
        self.assertEqual(Complex(Size(64)).as_python_type(), complex)
        self.assertEqual(Complex(Size(128)).as_python_type(), complex)

        # compound
        self.assertEqual(Tuple([int, bool]).as_python_type(),
                         typing.Tuple[int, bool])
        self.assertEqual(Tuple([int, Tuple([int, bool])]).as_python_type(),
                         typing.Tuple[int, typing.Tuple[int, bool]])
        self.assertEqual(Array(int, Size(3)).as_python_type(),
                         typing.List[int])

        self.assertEqual(Str().as_python_type(), str)
        self.assertEqual(Str(Size(10)).as_python_type(), str)

        self.assertEqual(Record(RecBI).as_python_type(), RecBI)
        self.assertEqual(Record(RecBDi).as_python_type(), RecBDi)
        self.assertNotEqual(Record(RecBI).as_python_type(), RecBI_copy)

        # compound: Union
        self.assertEqual(Union([bool, int]).as_python_type(),
                         typing.Union[bool, int])
        self.assertEqual(Union([bool, Tuple([int, bool])]).as_python_type(),
                         typing.Union[bool, typing.Tuple[int, bool]])

    def test_types_comparison(self):
        """Various tests of types comparison."""
        # primitive
        self.assertEqual(Int(Size(32)), Int())
        self.assertNotEqual(Int(), UInt())
        self.assertNotEqual(Int(), Int(Size(64)))

        # compound
        self.assertEqual(Tuple([int, bool]), Tuple([int, bool]))
        self.assertNotEqual(Tuple([int, bool]), Tuple([bool, int]))
        self.assertEqual(Array(int, Size(4)), Array(int, Size(4)))
        self.assertEqual(Array(int, Size(4)), Array(Int(), Size(4)))
        self.assertNotEqual(Array(int, Size(4)), Array(int, Size(5)))
        self.assertNotEqual(Str(), Str(Size(100)))
        self.assertEqual(Record(RecBI), Record(RecBI))

        # compound: Union
        self.assertEqual(Union([int, bool]), Union([bool, int]))
        self.assertEqual(Union([int, Union([int, bool])]),
                         Union([int, bool]))
        self.assertEqual(Union([int, Union([int, Union([int, bool])])]),
                         Union([int, bool]))
        self.assertEqual(Union([int, int]), Union([int]))
        self.assertNotEqual(Union([Int()]), Int())

    def test_Union(self):
        """Union specific types."""

        with self.assertRaises(DeltaTypeError):
            Union([])

        with self.assertRaises(DeltaTypeError):
            Union([None])

        with self.assertRaises(DeltaTypeError):
            Union([None, int])

    def test_top_not_allowed(self):
        """Compound types should not accept Top as a sub-type."""

        with self.assertRaises(DeltaTypeError):
            Array(object, Size(5))

        with self.assertRaises(DeltaTypeError):
            Tuple([object, int])

        with self.assertRaises(DeltaTypeError):
            Record(RecBT)

        with self.assertRaises(DeltaTypeError):
            Raw(object)

        with self.assertRaises(DeltaTypeError):
            Union([int, bool, object])

    def test_top_not_allowed(self):
        """Compound types should not accept Top as a sub-type."""

        with self.assertRaises(DeltaTypeError):
            Array(object, Size(5))

        with self.assertRaises(DeltaTypeError):
            Tuple([object, int])

        with self.assertRaises(DeltaTypeError):
            Record(RecBT)

        with self.assertRaises(DeltaTypeError):
            Raw(object)

        with self.assertRaises(DeltaTypeError):
            Union([int, bool, object])


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

    def check_float(self, val, t: Float):
        """Test pack-unpack for floats."""
        if not isinstance(t, Float):
            raise DeltaTypeError

        # TODO this check can be done on binary, then the number of places
        # will be more reasonably explained
        if t.size == Size(32):
            places = 7
        elif t.size == Size(64):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.pack_unpack(val, t)
        self.assertAlmostEqual(val, val_new, places=places)

    def check_complex(self, val, t: Complex):
        """Test pack-unpack for complex numbers."""
        if not isinstance(t, Complex):
            raise DeltaTypeError

        # Using the same idea as check_float, but for real and imaginary parts
        if t.size == Size(64):
            places = 7
        elif t.size == Size(128):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.pack_unpack(val, t)
        self.assertAlmostEqual(val.real, val_new.real, places=places)
        self.assertAlmostEqual(val.imag, val_new.imag, places=places)

    def test_Int(self):
        """Only 8, 16, 32, and 64 bits are supported."""
        for bits in (8, 16, 32, 64):
            self.check(-2**(bits-1), Int(Size(bits)))
            self.check(2**(bits-1) - 1, Int(Size(bits)))
            for _ in range(1000):
                self.check(random.randint(-2**(bits-1), 2**(bits-1) - 1),
                           Int(Size(bits)))

            # Booleans can be packed
            self.check(True, Int(Size(bits)))
            self.check(False, Int(Size(bits)))

            # Floats, strings and overflowing or
            # complex numbers are not packable
            self.assertFalse(Int(Size(bits)).is_packable(3.5))
            self.assertFalse(Int(Size(bits)).is_packable(3.0))
            self.assertFalse(Int(Size(bits)).is_packable("abc"))
            self.assertFalse(Int(Size(bits)).is_packable(2**bits-1))
            self.assertFalse(Int(Size(bits)).is_packable(3+5j))

    def test_UInt(self):
        """Only 8, 16, 32, and 64 bits are supported."""
        for bits in (8, 16, 32, 64):
            self.check(0, UInt(Size(bits)))
            self.check(2**bits - 1, UInt(Size(bits)))
            for _ in range(1000):
                self.check(random.randint(0, 2**bits - 1),
                           UInt(Size(bits)))

            # Booleans can be packed
            self.check(True, UInt(Size(bits)))
            self.check(False, UInt(Size(bits)))

            # Floats, strings and negative or complex numbers are not packable
            self.assertFalse(UInt(Size(bits)).is_packable(3.5))
            self.assertFalse(UInt(Size(bits)).is_packable(3.0))
            self.assertFalse(UInt(Size(bits)).is_packable("abc"))
            self.assertFalse(UInt(Size(bits)).is_packable(-2))
            self.assertFalse(UInt(Size(bits)).is_packable(3+5j))

    def test_Bool(self):
        self.check(False, Bool())
        self.check(0, Bool())
        self.check(True, Bool())
        self.check(1, Bool())

        # Floats, strings, complex numbers and integers
        # other than 0/1 are not packable
        self.assertFalse(Bool().is_packable(3.5))
        self.assertFalse(Bool().is_packable(3.0))
        self.assertFalse(Bool().is_packable("abc"))
        self.assertFalse(Bool().is_packable(3+5j))
        self.assertFalse(Bool().is_packable(4))
        self.assertFalse(Bool().is_packable(-2))

    def test_Float(self):
        """Only 32 and 64 bits are supported."""
        precision_dict = {32: -23, 64: -52}

        for bits, precision in precision_dict.items():
            for _ in range(1000):
                self.check_float(random.uniform(-1, 1), Float(Size(bits)))

            self.check(1 + 2**precision, Float(Size(bits)))

            # Booleans and ints can be packed
            self.check(True, Float(Size(bits)))
            self.check(False, Float(Size(bits)))
            self.check(3, Float(Size(bits)))

            # Strings and complex numbers are not packable
            self.assertFalse(Float(Size(bits)).is_packable("abc"))
            self.assertFalse(Float(Size(bits)).is_packable(3+5j))

    def test_Complex(self):
        """Only 64 and 128 bits are supported."""
        for bits in (64, 128):
            for _ in range(1000):
                self.check_complex(random.uniform(-1, 1) +
                                   random.uniform(-1, 1) * 1j,
                                   Complex(Size(bits)))

            # Booleans, ints and floats can be packed
            self.check(True, Complex(Size(bits)))
            self.check(False, Complex(Size(bits)))
            self.check(3, Complex(Size(bits)))
            self.check(3.5, Complex(Size(bits)))

            # Strings are not packable
            self.assertFalse(Complex(Size(bits)).is_packable("abc"))

    def test_Array(self):
        # primitive elements are properly handled
        # int are passed as Int, not UInt
        self.check([1, 2, 3], Array(Int(), Size(3)))

        # for floats use a dot
        # might be a potential problem, due to python silent type downcasting
        self.check([1.0, 2.0, 3.0], Array(Float(), Size(3)))

        # bool are passed as Bool, not Int
        self.check([True, False, False], Array(Bool(), Size(3)))

        # encapsulation of compound types
        self.check([[1, 2, 3], [4, 5, 6]],
                   Array(Array(Int(), Size(3)), Size(2)))

        with self.assertRaises(DeltaTypeError):
            self.check([1, 2, 3, 4, 5, 6],
                       Array(Array(Int(), Size(3)), Size(2)))

        with self.assertRaises(AssertionError):
            self.check([1, 2, 3, 4, 5, 6],
                       Array(Int(), Size(6)),
                       Array(Array(Int(), Size(3)), Size(2)))

        # mixed types
        self.check([(1, 2, 3), (4, 5, 6)],
                   Array(Tuple([int, int, int]), Size(2)))

        self.check(["hello", "world"], Array(Str(Size(5)), Size(2)))

        # numpy
        self.check_numpy([1, 2, 3, 4, 5], Array(int, Size(5)))

    def test_Str(self):
        self.check('hello world', Str())
        self.check('A' * 1024, Str())
        self.check('check digits 14213', Str())
        self.check('check spaces in the end ', Str())

        with self.assertRaises(DeltaTypeError):
            self.check('123456', Str(Size(4)))

        self.check((-5, 'text'), Tuple([int, Str()]))
        self.check(['hello', 'world!'], Array(Str(), Size(2)))

        self.check_numpy('hello world', Str())

    def test_Tuple(self):
        # primitive elements are properly handled
        self.check((-5, True, 3.25), Tuple([int, bool, float]))

        with self.assertRaises(DeltaTypeError):
            self.check((-5, True, 3.25), Tuple([int, bool, int]))

        # incapsulation
        self.check((-5, (1, 2)), Tuple([int, Tuple([int, int])]))

        with self.assertRaises(AssertionError):
            self.check((-5, (1, 2)),
                       Tuple([int, Tuple([int, int])]),
                       Tuple([int, int, int]))

        # mixed types
        self.check(([1, 2, 3], [4.0, 5.0]),
                   Tuple([Array(int, Size(3)), Array(float, Size(2))]))

        self.check(("hello", "world"), Tuple([Str(), Str(Size(6))]))

        # numpy
        self.check_numpy((1, 2.0, True), Tuple([int, float, bool]))

    def test_Record(self):
        # primitive
        self.check(RecBI(True, 5), Record(RecBI))
        self.check(-4, Int())
        self.check(RecBII(True, 5, -4), Record(RecBII))
        with self.assertRaises(DeltaTypeError):
            self.check(RecBI(True, 5), Record(RecIB))

        # mixed
        self.check(RecIT(-4.0, (1, 2)), Record(RecIT))
        self.check(RecATI([1, 2], (3.0, 4), 5),
                   Record(RecATI))

        self.check((RecIT(-4.0, (1, 2)), 1),
                   Tuple([Record(RecIT), int]))

        self.check([RecIT(-4.0, (1, 2)), RecIT(5.0, (-3, -4))],
                   Array(Record(RecIT), Size(2)))

        # numpy
        self.check_numpy(RecBI(False, 2), Record(RecBI))

    def test_Union(self):
        # primitive
        self.check(5, Union([int, bool]), Union([int, bool]))
        self.check(True, Union([int, bool]), Union([bool, int]))

        # compound
        self.check(5, Union([int, Tuple([int, float])]))
        self.check((4, 5), Union([int, Tuple([int, int])]))
        self.check((4, 5),
                   Union([Array(int, Size(2)), Tuple([int, int])]))
        self.check([4, 5],
                   Union([Array(int, Size(2)), Tuple([int, int])]))

        # buffer's size is always the same
        self.assertEqual(len(Union([int, bool]).pack(5)),
                         Union([int, bool]).size.val)
        self.assertEqual(len(Union([int, bool]).pack(True)),
                         Union([int, bool]).size.val)

        # numpy (throws error)
        with self.assertRaises(
                DeltaTypeError,
                msg="NumPy unions cannot be converted to Python types."):
            self.check_numpy(5, Union([bool, float, int]))


class WiresTest(unittest.TestCase):
    """Testing the rules of data transmission in a single wire of DeltaGraph."""

    def test_primitive_types(self):
        """Strict typing without subtyping."""
        self.assertTrue(DeltaGraph.check_wire(Int(), Int()))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Int(), UInt())

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(UInt(), Int())

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(int, int)

    def test_Top(self):
        """Everything can be accepted as Top()."""
        self.assertTrue(DeltaGraph.check_wire(Int(), Top()))
        self.assertTrue(DeltaGraph.check_wire(UInt(), Top()))
        self.assertTrue(DeltaGraph.check_wire(Bool(), Top()))
        self.assertTrue(DeltaGraph.check_wire(Tuple([int, bool]), Top()))
        self.assertTrue(DeltaGraph.check_wire(Union([int, bool]), Top()))
        self.assertTrue(DeltaGraph.check_wire(Array(int, Size(8)), Top()))
        self.assertTrue(DeltaGraph.check_wire(Str(), Top()))
        self.assertTrue(DeltaGraph.check_wire(Record(RecBI), Top()))

        # however this isn't true if allow_top is set to False
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Int(), Top(), allow_top=False)
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(UInt(), Top(), allow_top=False)
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Bool(), Top(), allow_top=False)
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Tuple([int, bool]), Top(), allow_top=False)
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Union([int, bool]), Top(), allow_top=False)
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Array(int, Size(8)), Top(), allow_top=False)
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Str(), Top(), allow_top=False)
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Record(RecBI), Top(), allow_top=False)

        # the sending port cannot have type Top()
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Top(), Top())
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Top(), Int())
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Union([Int(), Top()]), Int())

    def test_Union(self):
        """Test wires with Union."""
        # examples of obvious behaiviour
        self.assertTrue(DeltaGraph.check_wire(Union([int, bool]),
                                              Union([int, bool])))
        self.assertTrue(DeltaGraph.check_wire(Union([int, bool]),
                                              Union([bool, int])))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Union([int, bool]), Int())
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Union([int, bool, float]),
                                  Union([int, bool]))

        # strict typing even with Union, i.e. all subtypes should match
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Union([bool, int]),
                                  Union([bool, int, float]))

        # Union changes packing method, thus these tests should fail
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Int(), Union([int]))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Union([int]), Int())

    def test_Array(self):
        """Only strict typing."""
        self.assertTrue(DeltaGraph.check_wire(Array(int, Size(8)),
                                              Array(int, Size(8))))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Array(int, Size(10)),
                                  Array(int, Size(8)))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Array(int, Size(8)),
                                  Array(int, Size(10)))

    def test_Tuple(self):
        """Only strict typing."""
        self.assertTrue(DeltaGraph.check_wire(Tuple([int, bool]),
                                              Tuple([int, bool])))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Tuple([int, bool]),
                                  Tuple([bool, int]))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Tuple([int, bool]),
                                  Tuple([int, bool, bool]))

    def test_Record(self):
        """Only strict typing."""
        self.assertTrue(DeltaGraph.check_wire(Record(RecBI), Record(RecBI)))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Record(RecBI), Record(RecIB))

        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Record(RecBIS), Record(RecBI))


class UtilsTest(unittest.TestCase):
    """Helper functions."""

    def test_as_delta_type(self):
        """Test conversion from python to Deltaflow data types."""
        # special
        self.assertEqual(as_delta_type(object), Top())
        self.assertEqual(as_delta_type(type(object)), Top())
        self.assertEqual(as_delta_type(type), Top())
        self.assertEqual(as_delta_type('random_text'), Top())

        with self.assertRaises(DeltaTypeError):
            as_delta_type(None)
        with self.assertRaises(DeltaTypeError):
            as_delta_type(type(None))

        # primitive
        self.assertNotEqual(as_delta_type(bool), UInt(Size(1)))
        self.assertEqual(as_delta_type(bool), Bool())
        self.assertEqual(as_delta_type(np.bool_), Bool())
        self.assertEqual(as_delta_type(int), Int(Size(32)))
        self.assertEqual(as_delta_type(np.int8), Char())
        self.assertEqual(as_delta_type(np.int16), Int(Size(16)))
        self.assertEqual(as_delta_type(np.int32), Int(Size(32)))
        self.assertEqual(as_delta_type(np.int64), Int(Size(64)))
        self.assertEqual(as_delta_type(np.uint8), Char())
        self.assertEqual(as_delta_type(np.uint16), UInt(Size(16)))
        self.assertEqual(as_delta_type(np.uint32), UInt(Size(32)))
        self.assertEqual(as_delta_type(np.uint64), UInt(Size(64)))
        self.assertEqual(as_delta_type(float), Float())
        self.assertEqual(as_delta_type(np.float32), Float(Size(32)))
        self.assertEqual(as_delta_type(np.float64), Float(Size(64)))
        self.assertEqual(as_delta_type(complex), Complex())
        self.assertEqual(as_delta_type(np.complex64), Complex(Size(64)))
        self.assertEqual(as_delta_type(np.complex128), Complex(Size(128)))

        # compound
        with self.assertRaises(DeltaTypeError):
            as_delta_type(typing.Tuple[int, bool])
        with self.assertRaises(DeltaTypeError):
            as_delta_type(typing.List[int])
        self.assertNotEqual(as_delta_type(str), Array(Char(), Size(1024)))
        self.assertEqual(as_delta_type(str), Str())
        self.assertEqual(as_delta_type(RecBI), Record(RecBI))

        # numpy compound
        self.assertEqual(as_delta_type(Array(int, Size(5)).as_numpy_type()),
                         Array(int, Size(5)))
        self.assertEqual(as_delta_type(Str().as_numpy_type()), Str())
        self.assertEqual(
            as_delta_type(Tuple([int, bool, float]).as_numpy_type()),
            Tuple([int, bool, float])
        )
        self.assertEqual(as_delta_type(Record(RecBI).as_numpy_type()),
                         Record(RecBI))
        self.assertEqual(
            as_delta_type(Union([bool, float, int]).as_numpy_type()),
            Union([bool, float, int]))

        # from string
        self.assertEqual(as_delta_type('bool'), Bool())
        self.assertEqual(as_delta_type('\'bool\''), Bool())
        self.assertEqual(as_delta_type('np.bool_'), Bool())
        self.assertEqual(as_delta_type('int'), Int(Size(32)))
        self.assertEqual(as_delta_type('np.int32'), Int(Size(32)))
        self.assertEqual(as_delta_type('np.uint32'), UInt(Size(32)))
        self.assertEqual(as_delta_type('float'), Float())
        self.assertEqual(as_delta_type('np.float32'), Float(Size(32)))
        self.assertEqual(as_delta_type('complex'), Complex())
        self.assertEqual(as_delta_type('np.complex64'), Complex(Size(64)))
        self.assertEqual(as_delta_type('str'), Str())
        self.assertEqual(as_delta_type("Int(Size(32))"), Int(Size(32)))
        # 'RecBI' is out of scope when the string is evaluated
        self.assertEqual(as_delta_type('RecBI'), Top())

    def test_delta_type(self):
        """Test mapping python objects to Deltaflow data types."""
        # special
        with self.assertRaises(DeltaTypeError):
            delta_type(None)

        # primitive
        self.assertEqual(delta_type(False), Bool())
        self.assertEqual(delta_type(np.bool_(False)), Bool())
        self.assertEqual(delta_type(5), Int(Size(32)))
        self.assertEqual(delta_type(np.int16(5)), Int(Size(16)))
        self.assertEqual(delta_type(np.int32(5)), Int(Size(32)))
        self.assertEqual(delta_type(np.int64(5)), Int(Size(64)))
        self.assertEqual(delta_type(np.uint16(5)), UInt(Size(16)))
        self.assertEqual(delta_type(np.uint32(5)), UInt(Size(32)))
        self.assertEqual(delta_type(np.uint64(5)), UInt(Size(64)))
        self.assertEqual(delta_type(4.2), Float(Size(32)))
        self.assertEqual(delta_type(np.float32(4.2)), Float(Size(32)))
        self.assertEqual(delta_type(np.float64(4.2)), Float(Size(64)))
        self.assertEqual(delta_type(3+1j), Complex(Size(64)))
        self.assertEqual(delta_type(np.complex64(3+1j)), Complex(Size(64)))
        self.assertEqual(delta_type(np.complex128(3+1j)), Complex(Size(128)))
        self.assertEqual(delta_type('c'), Char())

        # compound
        self.assertEqual(delta_type((1, True, 3.7)),
                         Tuple([int, bool, float]))
        self.assertEqual(delta_type([1, 2, 4]), Array(int, Size(3)))
        self.assertEqual(delta_type(RecBI(True, 5)), Record(RecBI))

        # numpy compound
        self.assertEqual(delta_type(np.array([1, 2, 3, 4, 5])),
                         Array(Int(Size(64)), Size(5)))
        self.assertEqual(delta_type(np.array([1, 2.0, 3, 4, 5])),
                         Array(Float(Size(64)), Size(5)))
        self.assertEqual(delta_type(
            Str(Size(5)).as_numpy_object("abcde")), Str(Size(5)))
        self.assertEqual(
            delta_type(Tuple([int, float, bool]
                             ).as_numpy_object((1, 2.0, True))),
            Tuple([int, float, bool])
        )
        self.assertEqual(
            delta_type(Record(RecBI).as_numpy_object(RecBI(True, 2))),
            Record(RecBI)
        )
        self.assertEqual(
            delta_type(Union([bool, float, int]).as_numpy_object(5.0)),
            Union([bool, float, int])
        )

        # different combinations
        self.assertEqual(delta_type([(4, 4.3), (2, 3.3)]),
                         Array(Tuple([int, float]), Size(2)))


class DeltaTypesNumpyTest(unittest.TestCase):
    """Test from_numpy_object/as_numpy_object methods for `BaseDeltaType`.

    .. todo::
        Can be rewritten to inherit from DeltaTypesPackTest.
        The only possible exception is the Union test as that one is only
        one-way.
    """

    def to_np_and_back(self, val, t):
        return t.from_numpy_object(t.as_numpy_object(val))

    def check(self, val, t):
        self.assertEqual(self.to_np_and_back(val, t), val)

    def check_float(self, val, t: Float):
        """Test pack-unpack for floats."""
        if not isinstance(t, Float):
            raise DeltaTypeError

        # TODO this check can be done on binary, then the number of places
        # will be more reasonably explained
        if t.size == Size(32):
            places = 6
        elif t.size == Size(64):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.to_np_and_back(val, t)
        self.assertAlmostEqual(val, val_new, places=places)

    def check_complex(self, val, t: Complex):
        """Test pack-unpack for complex numbers."""
        if not isinstance(t, Complex):
            raise DeltaTypeError

        # Using the same idea as check_float, but for real and imaginary parts
        if t.size == Size(64):
            places = 6
        elif t.size == Size(128):
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

    def test_Bool(self):
        self.assertEqual(Bool().as_numpy_type(), np.bool_)

    def test_Bool_object(self):
        self.check(False, Bool())

    def test_Int_type(self):
        self.assertEqual(Int(Size(8)).as_numpy_type(), np.int8)
        self.assertEqual(Int(Size(16)).as_numpy_type(), np.int16)
        self.assertEqual(Int(Size(32)).as_numpy_type(), np.int32)
        self.assertEqual(Int(Size(64)).as_numpy_type(), np.int64)
        with self.assertRaises(NotImplementedError):
            Int(Size(128)).as_numpy_type()

    def test_Int_object(self):
        self.check(5, Int(Size(8)))
        self.check(10, Int(Size(16)))
        self.check(15, Int(Size(32)))
        self.check(20, Int(Size(64)))

    def test_UInt_type(self):
        self.assertEqual(UInt(Size(8)).as_numpy_type(), np.uint8)
        self.assertEqual(UInt(Size(16)).as_numpy_type(), np.uint16)
        self.assertEqual(UInt(Size(32)).as_numpy_type(), np.uint32)
        self.assertEqual(UInt(Size(64)).as_numpy_type(), np.uint64)
        with self.assertRaises(NotImplementedError):
            UInt(Size(128)).as_numpy_type()

    def test_UInt_object(self):
        self.check(5, UInt(Size(8)))
        self.check(10, UInt(Size(16)))
        self.check(15, UInt(Size(32)))
        self.check(20, UInt(Size(64)))

    def test_Char_type(self):
        self.assertEqual(Char().as_numpy_type(), np.uint8)

    def test_Char_object(self):
        self.check('a', Char())

    def test_Float_type(self):
        self.assertEqual(Float(Size(32)).as_numpy_type(), np.float32)
        self.assertEqual(Float(Size(64)).as_numpy_type(), np.float64)
        with self.assertRaises(NotImplementedError):
            UInt(Size(128)).as_numpy_type()

    def test_Float_object(self):
        self.check_float(3.14, Float(Size(32)))
        self.check_float(6.28, Float(Size(64)))

    def test_Complex_type(self):
        self.assertEqual(Complex(Size(64)).as_numpy_type(), np.complex64)
        self.assertEqual(Complex(Size(128)).as_numpy_type(), np.complex128)

    def test_Complex_object(self):
        self.check_complex(1 + 0.5j, Complex(Size(64)))
        self.check_complex(5 + 0.2j, Complex(Size(128)))

    def test_Array_type(self):
        int_type = Array(int, Size(5)).as_numpy_type()
        self.assertEqual(int_type[0], (np.int32, (5,)))

    def test_Array_object(self):
        self.check([1, 2, 3, 4, 5], Array(int, Size(5)))

    def test_Str_type(self):
        str_type = Str(Size(32)).as_numpy_type()
        self.assertEqual(str_type, (np.string_, 32))

    def test_Str_object(self):
        self.check("abcde", Str(Size(32)))

    def test_Tuple_type(self):
        tuple_type = Tuple((int, bool, Char())).as_numpy_type()
        self.assertEqual(tuple_type[0], np.int32)
        self.assertEqual(tuple_type[1], np.bool_)
        self.assertEqual(tuple_type[2], np.uint8)

    def test_Tuple_object(self):
        t = Tuple((int, bool, Char()))
        self.check((5, True, 'c'), t)

    def test_Record_type(self):
        record_type = Record(RecBI).as_numpy_type()
        self.assertEqual(record_type['x'], np.bool_)
        self.assertEqual(record_type['y'], np.int32)

    def test_Record_object(self):
        rectangle = RecBI(True, 5)
        self.check(rectangle, Record(RecBI))

    def test_Union_type(self):
        union_type = Union([bool, Char(), int]).as_numpy_type()
        self.assertEqual(union_type[0], np.bool_)
        self.assertEqual(union_type[1], np.uint8)
        self.assertEqual(union_type[2], np.int32)
        self.assertEqual(union_type.fields['Bool'][1], 0)
        self.assertEqual(union_type.fields['Char8'][1], 0)
        self.assertEqual(union_type.fields['Int32'][1], 0)

    def test_Union_object(self):
        union_object = Union([bool, Char(), int]).as_numpy_object('c')
        self.assertEqual(union_object[0]["Char8"], 99)

        with self.assertRaises(
                DeltaTypeError,
                msg="NumPy unions cannot be converted to Python types."):
            self.check('c', Union([bool, Char(), int]))

    def test_compound_objects(self):
        t = Array(Tuple([bool, int]), Size(3))
        val = [(True, 1), (False, 2), (True, 3), (False, 4), (True, 5)]
        self.check(val, t)

        t = Tuple([int, Tuple([bool, int])])
        val = (12, (True, 8))
        self.check(val, t)

        t = Tuple([int, Array(int, Size(2))])
        val = (12, [14, 18])
        self.check(val, t)

        t = Tuple([int, Str()])
        val = (12, "hello")
        self.check(val, t)

        t = Tuple([int, Record(RecBI)])
        val = (12, RecBI(True, 8))
        self.check(val, t)

        t = Tuple([int, Union([bool, int])])
        val = (12, True)
        np_val = t.as_numpy_object(val)
        self.assertEqual(Int().from_numpy_object(np_val[0][0]), 12)
        self.assertEqual(Bool().from_numpy_object(np_val[0][1][1]), True)

        t = Record(RecATI)
        val = RecATI([1, 2], (3.0, 4), 5)
        self.check(val, t)

        t = Union([Array(int, Size(2)), int])
        val = [1, 2]
        np_val = t.as_numpy_object(val)
        new_val = Array(int, Size(2)).from_numpy_object(np_val[0][1])
        self.assertEqual(val, new_val)

        t = Union([str, int])
        val = "abcde"
        np_val = t.as_numpy_object(val)
        new_val = Str().from_numpy_object(np_val[0][1])
        self.assertEqual(val, new_val)


class RawTest(unittest.TestCase):
    """Test Raw packing/unpacking + transmission rules.

    .. todo::
        This test case repeats everything from DeltaTypesPackTest but with
        different check method, specifically for Raw. This code repetition
        can be reduced via inheritance.

        Plus there are checks how DeltaGraph.check_wire works with Raw.
        They can be moved to WiresTest.
    """

    def to_and_from_bits(self, val, base_type):
        """Helper that converts a value to and from bits via given type."""
        raw_type = Raw(base_type)
        return raw_type.from_bits(raw_type.as_bits(val))

    def pack_unpack(self, val, base_type):
        """Packs and unpacks a Raw type."""
        raw_type = Raw(base_type)
        packed = raw_type.pack(raw_type.as_bits(val))
        return raw_type.from_bits(raw_type.unpack(packed))

    def check_error(self, val, base_type):
        if not isinstance(val, int):
            with self.assertRaises(DeltaTypeError):
                Raw(base_type).pack(val)

    def check(self, val, t):
        """Test that to and from bits returns exactly the same message."""
        val_new = self.to_and_from_bits(val, t)
        self.assertEqual(val, val_new)
        val_new = self.pack_unpack(val, t)
        self.assertEqual(val, val_new)
        self.check_error(val, t)

    def check_float(self, val, t: Float):
        """Test for floats."""
        if not isinstance(t, Float):
            raise DeltaTypeError

        # TODO this check can be done on binary, then the number of places
        # will be more reasonably explained
        if t.size == Size(32):
            places = 7
        elif t.size == Size(64):
            places = 15
        else:
            raise NotImplementedError('Unsupported format')

        val_new = self.to_and_from_bits(val, t)
        self.assertAlmostEqual(val, val_new, places=places)
        val_new = self.pack_unpack(val, t)
        self.assertAlmostEqual(val, val_new, places=places)
        self.check_error(val, t)

    def check_complex(self, val, t: Complex):
        """Test for complex numbers."""
        if not isinstance(t, Complex):
            raise DeltaTypeError

        # Using the same idea as check_float, but for real and imaginary parts
        if t.size == Size(64):
            places = 7
        elif t.size == Size(128):
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

    def test_Int(self):
        """Only 8, 16, 32 and 64 bits are supported."""
        for bits in (8, 16, 32, 64):
            self.check(-2**(bits-1), Int(Size(bits)))
            self.check(2**(bits-1) - 1, Int(Size(bits)))
            for _ in range(1000):
                self.check(random.randint(-2**(bits-1), 2**(bits-1) - 1),
                           Int(Size(bits)))

        self.assertTrue(DeltaGraph.check_wire(Raw(int), Raw(int)))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Raw(Int(Size(32))),
                                  Raw(Int(Size(64))))

    def test_UInt(self):
        """Only 8, 16, 32 and 64 bits are supported."""
        for bits in (8, 16, 32, 64):
            self.check(0, UInt(Size(bits)))
            self.check(2**bits - 1, UInt(Size(bits)))
            for _ in range(1000):
                self.check(random.randint(0, 2**bits - 1),
                           UInt(Size(bits)))

        self.assertTrue(DeltaGraph.check_wire(Raw(UInt(Size(32))),
                                              Raw(UInt(Size(32)))))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Raw(UInt(Size(32))),
                                  Raw(UInt(Size(64))))

    def test_Bool(self):
        self.check(False, Bool())
        self.check(0, Bool())
        self.check(True, Bool())
        self.check(1, Bool())
        self.assertTrue(DeltaGraph.check_wire(Raw(Bool()), Raw(Bool())))

    def test_Float(self):
        """Only 32 and 64 bits are supported."""
        precision_dict = {32: -23, 64: -52}

        for bits, precision in precision_dict.items():
            for _ in range(1000):
                self.check_float(random.uniform(-1, 1), Float(Size(bits)))

            self.check(1 + 2**precision, Float(Size(bits)))

        self.assertTrue(DeltaGraph.check_wire(Raw(float), Raw(float)))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Raw(Float(Size(32))),
                                  Raw(Float(Size(64))))

    def test_Complex(self):
        """Only 64 and 128 bits are supported."""
        for bits in (64, 128):
            for _ in range(1000):
                self.check_complex(random.uniform(-1, 1) +
                                   random.uniform(-1, 1) * 1j,
                                   Complex(Size(bits)))

        self.assertTrue(DeltaGraph.check_wire(Raw(complex), Raw(complex)))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Raw(Complex(Size(64))),
                                  Raw(Complex(Size(128))))

    def test_Array(self):
        # primitive elements are properly handled
        # int are passed as Int, not UInt
        self.check([1, 2, 3], Array(Int(), Size(3)))

        # for floats use a dot
        # might be a potential problem, due to python silent type downcasting
        self.check([1.0, 2.0, 3.0], Array(Float(), Size(3)))

        # bool are passed as Bool, not Int
        self.check([True, False, False], Array(Bool(), Size(3)))

        # encapsulation of compound types
        self.check([[1, 2, 3], [4, 5, 6]],
                   Array(Array(Int(), Size(3)), Size(2)))

        # mixed types
        self.check([(1, 2, 3), (4, 5, 6)],
                   Array(Tuple([int, int, int]), Size(2)))

        self.check(["hello", "world"], Array(Str(Size(5)), Size(2)))
        self.assertTrue(DeltaGraph.check_wire(Raw(Array(int, Size(2))),
                                              Raw(Array(int, Size(2)))))
        with self.assertRaises(DeltaTypeError):
            DeltaGraph.check_wire(Raw(Array(int, Size(2))),
                                  Raw(Array(int, Size(3))))

    def test_Str(self):
        self.check('hello world', Str())
        self.check('A' * 1024, Str())
        self.check('check digits 14213', Str())
        self.check('check spaces in the end ', Str())

        self.check((-5, 'text'), Tuple([int, Str()]))
        self.check(['hello', 'world!'], Array(Str(), Size(2)))
        self.assertTrue(DeltaGraph.check_wire(Raw(Str()), Raw(Str())))

    def test_Tuple(self):
        # primitive elements are poperly handled
        self.check((-5, True, 3.25), Tuple([int, bool, float]))

        # incapsulation
        self.check((-5, (1, 2)), Tuple([int, Tuple([int, int])]))

        # mixed types
        self.check(([1, 2, 3], [4.0, 5.0]),
                   Tuple([Array(int, Size(3)), Array(float, Size(2))]))

        self.check(("hello", "world"), Tuple([Str(), Str(Size(6))]))
        self.assertTrue(DeltaGraph.check_wire(Raw(Tuple([Str(), int])),
                                              Raw(Tuple([Str(), int]))))

    def test_Record(self):
        # primitive
        self.check(RecBI(True, 5), Record(RecBI))
        self.check(-4, Int())
        self.check(RecBII(True, 5, -4), Record(RecBII))

        # mixed
        self.check(RecIT(-4.0, (1, 2)), Record(RecIT))
        self.check(RecATI([1, 2], (3.0, 4), 5),
                   Record(RecATI))

        self.check((RecIT(-4.0, (1, 2)), 1),
                   Tuple([Record(RecIT), int]))

        self.check([RecIT(-4.0, (1, 2)), RecIT(5.0, (-3, -4))],
                   Array(Record(RecIT), Size(2)))
        self.assertTrue(DeltaGraph.check_wire(Raw(Record(RecIT)),
                                              Raw(Record(RecIT))))

    def test_Union(self):
        # primitive
        self.check(5, Union([int, bool]))
        self.check(True, Union([int, bool]))

        # compound
        self.check(5, Union([int, Tuple([int, float])]))
        self.check((4, 5), Union([int, Tuple([int, int])]))
        self.check((4, 5),
                   Union([Array(int, Size(2)), Tuple([int, int])]))
        self.check([4, 5],
                   Union([Array(int, Size(2)), Tuple([int, int])]))
        self.assertTrue(DeltaGraph.check_wire(Raw(Union([Str(), int])),
                                              Raw(Union([Str(), int]))))

        with self.assertRaises(DeltaTypeError):
            self.check("Can't pack me", Union([int, float]))


if __name__ == "__main__":
    unittest.main()
