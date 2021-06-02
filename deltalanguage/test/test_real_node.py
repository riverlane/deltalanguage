from collections import OrderedDict
import unittest

import numpy as np

from deltalanguage.wiring import RealNode, PyConstBody, DeltaGraph, InPort


class RealNodeEq(unittest.TestCase):
    """Tests for the definition of equality over real nodes.
    """

    def test_eq(self):
        g1 = DeltaGraph()
        b1 = PyConstBody(lambda: 2, value=2)
        n1 = RealNode(g1, [b1], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')
        self.assertEqual(n1, n1)

        g2 = DeltaGraph()
        b2 = PyConstBody(lambda: 2, value=2)
        n2 = RealNode(g2, [b2], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')
        self.assertEqual(n1, n2)

    def test_eq_multi_body(self):
        g1 = DeltaGraph()
        b1_a = PyConstBody(lambda: 2, value=2)
        b1_b = PyConstBody(lambda: 3, value=3)
        n1 = RealNode(g1, [b1_a, b1_b], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')

        g2 = DeltaGraph()
        b2_a = PyConstBody(lambda: 2, value=2)
        b2_b = PyConstBody(lambda: 3, value=3)
        n2 = RealNode(g2, [b2_a, b2_b], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')
        self.assertEqual(n1, n2)

    def test_neq_body_diff(self):
        g1 = DeltaGraph()
        b1 = PyConstBody(lambda: 1, value=1)
        n1 = RealNode(g1, [b1], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')

        g2 = DeltaGraph()
        b2 = PyConstBody(lambda: 2, value=2)
        n2 = RealNode(g2, [b2], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')
        self.assertNotEqual(n1, n2)

    def test_neq_body_order(self):
        g1 = DeltaGraph()
        b1_a = PyConstBody(lambda: 2, value=2)
        b1_b = PyConstBody(lambda: 3, value=3)
        n1 = RealNode(g1, [b1_a, b1_b], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')

        g2 = DeltaGraph()
        b2_a = PyConstBody(lambda: 2, value=2)
        b2_b = PyConstBody(lambda: 3, value=3)
        n2 = RealNode(g2, [b2_b, b2_a], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')
        self.assertNotEqual(n1, n2)

    def test_neq_name_diff(self):
        g1 = DeltaGraph()
        b1 = PyConstBody(lambda: 2, value=2)
        n1 = RealNode(g1, [b1], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node_a')

        g2 = DeltaGraph()
        b2 = PyConstBody(lambda: 2, value=2)
        n2 = RealNode(g2, [b2], OrderedDict([('in', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node_b')
        self.assertNotEqual(n1, n2)

    def test_neq_inputs_diff(self):
        g1 = DeltaGraph()
        b1 = PyConstBody(lambda: 2, value=2)
        n1 = RealNode(g1, [b1], OrderedDict([('in_a', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')

        g2 = DeltaGraph()
        b2 = PyConstBody(lambda: 2, value=2)
        n2 = RealNode(g2, [b2], OrderedDict([('in_b', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')
        self.assertNotEqual(n1, n2)

    def test_neq_outputs_diff(self):
        g1 = DeltaGraph()
        b1 = PyConstBody(lambda: 2, value=2)
        n1 = RealNode(g1, [b1], OrderedDict([('in_a', int)]),
                      OrderedDict([('out', bool)]),
                      name='test_node')

        g2 = DeltaGraph()
        b2 = PyConstBody(lambda: 2, value=2)
        n2 = RealNode(g2, [b2], OrderedDict([('in_b', int)]),
                      OrderedDict([('out', bool), ('out_2', bool)]),
                      name='test_node')
        self.assertNotEqual(n1, n2)


class RealNodeAddOutPort(unittest.TestCase):
    """Test the behaviour of adding out ports to a real node.
    """

    def test_add_out_port_order(self):
        """Ensure that no matter what order out ports are added, they end up
        in the order specified in outputs.
        This property needs to hold even when not all ports are added.
        """
        g1 = DeltaGraph()
        n1 = RealNode(g1, [], OrderedDict(),
                      OrderedDict([('a', int), ('b', int),
                                   ('c', int), ('d', int)]),
                      name='test_node_out')
        n2 = RealNode(g1, [],
                      OrderedDict([('a', int), ('b', int),
                                   ('c', int), ('d', int)]),
                      OrderedDict(),
                      name='test_node_in')

        in_p_a = InPort('a', int, n2, 0)
        in_p_b = InPort('b', int, n2, 0)
        in_p_c = InPort('c', int, n2, 0)
        in_p_d = InPort('d', int, n2, 0)
        in_ports = [in_p_a, in_p_b, in_p_c, in_p_d]

        # Add all ports in random order
        for i in np.random.permutation(len(in_ports)):
            n1.add_out_port(in_ports[i], in_ports[i].index)

            # Check order is still correct
            p_order = []
            for out_port in n1.out_ports:
                out_port_index = list(n1.outputs).index(out_port.index)
                p_order.append(out_port_index)
            self.assertTrue(all(p_order[i] <= p_order[i+1]
                                for i in range(len(p_order)-1)))


if __name__ == "__main__":
    unittest.main()
