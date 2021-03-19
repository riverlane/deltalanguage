"""Testing InPort and OutPort classes."""

import unittest

from deltalanguage.data_types import DFloat, DInt, DOptional, DUnion
from deltalanguage._utils import NamespacedName
from deltalanguage.wiring import InPort, OutPort


class TestInPortDOptiona(unittest.TestCase):
    """This list of test shows that InPort accepts the expected data type
    when created and does the following simplification:
    if it's `DOptional(t)`, the port type becomes just `t`.
    """

    def test_non_DOptional(self):
        port = InPort(NamespacedName("test_name", None),
                      DInt(),
                      None,
                      0)
        self.assertEqual(port.port_type, DInt())
        self.assertEqual(port.is_optional, False)

    def test_DOptional(self):
        port = InPort(NamespacedName("test_name", None),
                      DOptional(DInt()),
                      None,
                      0)
        self.assertEqual(port.port_type, DInt())
        self.assertEqual(port.is_optional, True)

    def test_DUnion_of_single(self):
        """DUnion of a single type is not converted to a single type."""
        port = InPort(NamespacedName("test_name", None),
                      DUnion([DInt()]),
                      None,
                      0)
        self.assertEqual(port.port_type, DUnion([DInt()]))
        self.assertEqual(port.is_optional, False)

    def test_DUnion(self):
        port = InPort(NamespacedName("test_name", None),
                      DUnion([DInt(), DFloat()]),
                      None,
                      0)
        self.assertEqual(port.port_type, DUnion([DInt(), DFloat()]))
        self.assertEqual(port.is_optional, False)

    def test_DOptiona_of_DUnion(self):
        port = InPort(NamespacedName("test_name", None),
                      DOptional(DUnion([DInt(), DFloat()])),
                      None,
                      0)
        self.assertEqual(port.port_type, DUnion([DInt(), DFloat()]))
        self.assertEqual(port.is_optional, True)


class TestOutPortDOptiona(unittest.TestCase):
    """This list of test shows that OutPort data type cannot be `DOptional`."""

    def test_non_DOptional(self):
        port = OutPort(NamespacedName("test_name", None),
                       DInt(),
                       None,
                       None)
        self.assertEqual(port.port_type, DInt())

    def test_DOptional(self):
        port = OutPort(NamespacedName("test_name", None),
                       DOptional(DInt()),
                       None,
                       None)
        with self.assertRaises(TypeError):
            dummy = port.port_type


if __name__ == "__main__":
    unittest.main()
