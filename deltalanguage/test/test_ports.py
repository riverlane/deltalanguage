"""Testing InPort and OutPort classes."""

import unittest

from deltalanguage.data_types import Float, Int, Optional, Union
from deltalanguage.wiring import InPort, OutPort


class TestInPortDOptiona(unittest.TestCase):
    """This list of test shows that InPort accepts the expected data type
    when created and does the following simplification:
    if it's `Optional(t)`, the port type becomes just `t`.
    """

    def test_non_Optional(self):
        port = InPort(None,
                      Int(),
                      None,
                      0)
        self.assertEqual(port.port_type, Int())
        self.assertEqual(port.is_optional, False)

    def test_Optional(self):
        port = InPort(None,
                      Optional(Int()),
                      None,
                      0)
        self.assertEqual(port.port_type, Int())
        self.assertEqual(port.is_optional, True)

    def test_Union_of_single(self):
        """Union of a single type is not converted to a single type."""
        port = InPort(None,
                      Union([Int()]),
                      None,
                      0)
        self.assertEqual(port.port_type, Union([Int()]))
        self.assertEqual(port.is_optional, False)

    def test_Union(self):
        port = InPort(None,
                      Union([Int(), Float()]),
                      None,
                      0)
        self.assertEqual(port.port_type, Union([Int(), Float()]))
        self.assertEqual(port.is_optional, False)

    def test_Optional_of_Union(self):
        port = InPort(None,
                      Optional(Union([Int(), Float()])),
                      None,
                      0)
        self.assertEqual(port.port_type, Union([Int(), Float()]))
        self.assertEqual(port.is_optional, True)


class TestOutPortDOptiona(unittest.TestCase):
    """This list of test shows that OutPort data type cannot be `Optional`."""

    def test_non_Optional(self):
        port = OutPort(None,
                       Int(),
                       None,
                       None)
        self.assertEqual(port.port_type, Int())

    def test_Optional(self):
        port = OutPort(None,
                       Optional(Int()),
                       None,
                       None)
        with self.assertRaises(TypeError):
            dummy = port.port_type


if __name__ == "__main__":
    unittest.main()
