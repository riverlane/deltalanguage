"""Testing InPort and OutPort classes."""
from collections import OrderedDict
import unittest

from deltalanguage.data_types import Float, Int, Optional, Union
from deltalanguage.wiring import InPort, OutPort, DeltaGraph, RealNode


class TestInPortOptional(unittest.TestCase):
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


class TestInPortEq(unittest.TestCase):
    """Test the equality function over in-ports, both for equivalent and
    non-equivalent pairs of in-ports.
    """

    def test_eq(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        in_p_1 = InPort('a', int, n1, 0)
        self.assertEqual(in_p_1, in_p_1)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict([('a', int)]), OrderedDict())
        in_p_2 = InPort('a', int, n2, 0)
        self.assertEqual(in_p_1, in_p_2)

    def test_eq_optional(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict(
            [('a', Optional(int))]), OrderedDict())
        in_p_1 = InPort('a', Optional(int), n1, 0)
        self.assertEqual(in_p_1, in_p_1)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict(
            [('a', Optional(int))]), OrderedDict())
        in_p_2 = InPort('a', Optional(int), n2, 0)
        self.assertEqual(in_p_1, in_p_2)

    def test_neq_optional_diff(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        in_p_1 = InPort('a', int, n1, 0)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict(
            [('a', Optional(int))]), OrderedDict())
        in_p_2 = InPort('a', Optional(int), n2, 0)
        self.assertNotEqual(in_p_1, in_p_2)

    def test_neq_index_diff(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict([('b', int)]), OrderedDict())
        in_p_1 = InPort('b', int, n1, 0)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict([('a', int)]), OrderedDict())
        in_p_2 = InPort('a', int, n2, 0)
        self.assertNotEqual(in_p_1, in_p_2)

    def test_neq_type_diff(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        in_p_1 = InPort('a', int, n1, 0)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict([('a', float)]), OrderedDict())
        in_p_2 = InPort('a', float, n2, 0)
        self.assertNotEqual(in_p_1, in_p_2)

    def test_neq_node_diff(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        in_p_1 = InPort('a', int, n1, 0)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict(
            [('a', int), ('b', int)]), OrderedDict())
        in_p_2 = InPort('a', int, n2, 0)
        self.assertNotEqual(in_p_1, in_p_2)

    def test_neq_size_diff(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        in_p_1 = InPort('a', int, n1, 0)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict([('a', int)]), OrderedDict())
        in_p_2 = InPort('a', int, n2, 2)
        self.assertNotEqual(in_p_1, in_p_2)


class TestOutPortEq(unittest.TestCase):
    """Test the equality function over out-ports, both for equivalent and
    non-equivalent pairs of out-ports.
    """

    def test_eq(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict(), OrderedDict([('out_a', int)]))
        dest_n_1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        dest_1 = InPort('a', int, dest_n_1, 0)
        out_p_1 = OutPort('out_a', int, dest_1, n1)
        self.assertEqual(out_p_1, out_p_1)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict(), OrderedDict([('out_a', int)]))
        dest_n_2 = RealNode(g2, [], OrderedDict([('a', int)]), OrderedDict())
        dest_2 = InPort('a', int, dest_n_2, 0)
        out_p_2 = OutPort('out_a', int, dest_2, n2)
        self.assertEqual(out_p_1, out_p_2)

    def test_neq_index_diff(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict(), OrderedDict([('out_a', int)]))
        dest_n_1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        dest_1 = InPort('a', int, dest_n_1, 0)
        out_p_1 = OutPort('out_a', int, dest_1, n1)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict(), OrderedDict([('out_a', int)]))
        dest_n_2 = RealNode(g2, [], OrderedDict([('a', int)]), OrderedDict())
        dest_2 = InPort('a', int, dest_n_2, 0)
        out_p_2 = OutPort('out_b', int, dest_2, n2)
        self.assertNotEqual(out_p_1, out_p_2)
        
    def test_neq_type_diff(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict(), OrderedDict([('out_a', int)]))
        dest_n_1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        dest_1 = InPort('a', int, dest_n_1, 0)
        out_p_1 = OutPort('out_a', int, dest_1, n1)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict(), OrderedDict([('out_a', int)]))
        dest_n_2 = RealNode(g2, [], OrderedDict([('a', int)]), OrderedDict())
        dest_2 = InPort('a', int, dest_n_2, 0)
        out_p_2 = OutPort('out_a', float, dest_2, n2)
        self.assertNotEqual(out_p_1, out_p_2)

    def test_neq_dest_diff(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict(), OrderedDict([('out_a', int)]))
        dest_n_1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        dest_1 = InPort('a', int, dest_n_1, 0)
        out_p_1 = OutPort('out_a', int, dest_1, n1)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict(), OrderedDict([('out_a', int)]))
        dest_n_2 = RealNode(g2, [], OrderedDict([('a', int)]), OrderedDict())
        dest_2 = InPort('b', int, dest_n_2, 0)
        out_p_2 = OutPort('out_a', int, dest_2, n2)
        self.assertNotEqual(out_p_1, out_p_2)

    def test_neq_node_diff(self):
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict(), OrderedDict([('out_a', int)]))
        dest_n_1 = RealNode(g1, [], OrderedDict([('a', int)]), OrderedDict())
        dest_1 = InPort('a', int, dest_n_1, 0)
        out_p_1 = OutPort('out_a', int, dest_1, n1)

        g2 = DeltaGraph()
        n2 = RealNode(g2, [], OrderedDict([('c', bool)]), OrderedDict([('out_a', int)]))
        dest_n_2 = RealNode(g2, [], OrderedDict([('a', int)]), OrderedDict())
        dest_2 = InPort('a', int, dest_n_2, 0)
        out_p_2 = OutPort('out_a', int, dest_2, n2)
        self.assertNotEqual(out_p_1, out_p_2)

class TestOutPortOptional(unittest.TestCase):
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
