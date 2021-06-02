"""Test of DeltaGraph class."""

import os
from typing import Tuple
import unittest

import deltalanguage as dl
from deltalanguage.data_types import DeltaTypeError
from deltalanguage.test._node_lib import return_1_const


@dl.DeltaBlock(outputs=[('a', int), ('b', bool), ('c', int), ('d', int)])
def forked_return_output(x: dl.Int(dl.Size(8)),
                         y: dl.Int(dl.Size(8))
                         ) -> Tuple[int, bool, int, int]:
    return 0, 1, 1, 0


@dl.DeltaBlock(allow_const=False)
def multi_body_no_output(i: dl.Int(dl.Size(8))) -> dl.Void:
    print(i)


class Foo():

    def __init__(self):
        pass

    @dl.DeltaMethodBlock()
    def method_func_no_output(self, i: dl.Int(dl.Size(8))) -> dl.Void:
        print(i + 1)


class MigenFoo(dl.MigenNodeTemplate):
    def migen_body(self, template):
        template.add_pa_in_port('i', dl.Optional(dl.Int(dl.Size(8))))


@dl.Interactive([('i', dl.Int(dl.Size(8)))])
def interactive_func_no_output(node: dl.RealNode):
    node.receive('i')


template_no_output_no_body = dl.NodeTemplate(
    name="template_no_output_no_body",
    inputs=[('i', dl.Int(dl.Size(8)))]
)


@dl.DeltaBlock()
def experiment_stopper(completed: dl.Int(dl.Size(8))) -> dl.Void:
    raise dl.DeltaRuntimeExit


class DeltaGraphTest(unittest.TestCase):
    """Check rules used by ``DeltaGraph.check``."""

    def test_loose_output(self):
        """Loose output wire don't cause a problem"""
        s = dl.lib.StateSaver(int)
        with dl.DeltaGraph() as graph:
            s.transfer(4)

        node = graph.find_node_by_name('transfer')
        self.assertTrue(len(node.out_ports) == 0)
        self.assertTrue(graph.check())

    def test_loose_input(self):
        """Loose input wire is bad."""
        s = dl.lib.StateSaver(int)
        with dl.DeltaGraph() as graph:
            p = dl.placeholder_node_factory()
            s.transfer(p)

        with self.assertRaises(dl.data_types.DeltaIOError):
            graph.check()

    def test_loose_optional_input(self):
        """Optional input without input does not raise an error."""
        @dl.DeltaBlock(allow_const=False)
        def test_node(a: dl.Optional(int)) -> dl.Void:
            pass

        with dl.DeltaGraph() as graph:
            p = dl.placeholder_node_factory()
            test_node(p)

        self.assertTrue(graph.check())

    def test_allow_top(self):
        """Top is allowed by default"""
        s = dl.lib.StateSaver()
        with dl.DeltaGraph() as graph:
            s.save_and_exit(return_1_const())

        self.assertTrue(graph.check())

    def test_no_allow_top(self):
        """Top is not allowed by if allow_top set to False"""
        s = dl.lib.StateSaver()
        with dl.DeltaGraph() as graph:
            s.save_and_exit(4)

        with self.assertRaises(DeltaTypeError):
            graph.check(allow_top=False)


class DeltaGraphStrTest(unittest.TestCase):
    """Test for correct graph printing."""

    def test_graph_str_output(self):
        """Stringify a pre-defined graph and compare output to test data"""

        self.maxDiff = None
        dl.DeltaGraph.clean_stack()

        with dl.DeltaGraph() as graph:
            n1 = forked_return_output(1, 2)
            template_no_output_no_body.call(n1.a)
            n3 = multi_body_no_output(n1.b)
            MigenFoo().call(i=n1.d)
            experiment_stopper(n1.c)

        obj = Foo()
        n3.add_body(obj.method_func_no_output)
        n3.add_body(interactive_func_no_output)

        f = os.path.join('deltalanguage', 'test', 'data', 'graph_str.txt')
        with open(f, 'r') as file:
            correct_str = file.read()

        self.assertEqual(str(graph), correct_str)


class DeltaGraphWiringWrongInputTest(unittest.TestCase):
    """Error is raised when trying to provide an input to an in-port that
    is not defined.
    """

    def test_DeltaBlock(self):
        @dl.DeltaBlock()
        def foo(a: int) -> dl.Void:
            print(a)

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo(b=1)

    def test_DeltaMethodBlock(self):
        class AClass:

            @dl.DeltaMethodBlock()
            def add_x(self, a: int) -> dl.Void:
                print(a)

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                AClass().add_x(b=1)

    def test_Interactive(self):
        @dl.Interactive(inputs=[('a', int)])
        def foo(node):
            node.receive("a")

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo.call(b=1)

    def test_MigenNodeTemplate(self):
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', dl.Optional(int))

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                AMigenNode().call(b=1)


class DeltaGraphWiringNoOutputTest(unittest.TestCase):
    """Error is raised when trying to get an output from a node without defined
    out-ports.
    """

    def test_DeltaBlock(self):
        @dl.DeltaBlock()
        def foo(a: int) -> dl.Void:
            print(a)

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo(foo(1))

    def test_DeltaMethodBlock(self):
        class AClass:

            @dl.DeltaMethodBlock()
            def foo(self, a: int) -> dl.Void:
                print(a)

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                AClass().foo(AClass().foo(1))

    def test_Interactive(self):
        @dl.Interactive(inputs=[('a', int)])
        def foo(node):
            print(node.receive("a"))

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo.call(a=foo.call(a=1))

    def test_MigenNodeTemplate(self):
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', dl.Optional(int))

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                AMigenNode().call(a=AMigenNode().call(a=1))


class DeltaGraphWiringWrongOutputTest(unittest.TestCase):
    """Error is raised when trying to get an output from a node with multiple
    output ports, but use a wrong port name.
    """

    def test_DeltaBlock(self):
        @dl.DeltaBlock(outputs=[('x', int), ('y', int)])
        def foo(a: int):
            return 1, 2

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo(foo(1).z)

    def test_DeltaMethodBlock(self):
        class AClass:

            @dl.DeltaMethodBlock(outputs=[('x', int), ('y', int)])
            def foo(self, a: int):
                return 1, 2

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                AClass().foo(AClass().foo(1).z)

    def test_Interactive(self):
        @dl.Interactive([('a', int)], outputs=[('x', int), ('y', int)])
        def foo(node):
            node.send(x=1, y=2)

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo.call(a=foo.call(a=1).z)

    def test_MigenNodeTemplate(self):
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', dl.Optional(int))
                template.add_pa_out_port('x', int)
                template.add_pa_out_port('y', int)

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                AMigenNode().call(a=AMigenNode().call(a=1).z)

    def test_non_forked(self):
        @dl.DeltaBlock()
        def baa(a: int) -> int:
            return 1

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                baa(baa(1).z)


class DeltaGraphEquality(unittest.TestCase):
    """Tests for checking equality between two graphs.
    """

    def test_eq_func_and_const_graph(self):
        @dl.DeltaBlock()
        def baa(a: int) -> int:
            return 1

        with dl.DeltaGraph() as g1:
            baa(baa(1))

        with dl.DeltaGraph() as g2:
            baa(baa(1))

        self.assertEqual(g1, g2)

    def test_neq_pure_const_diff(self):
        @dl.DeltaBlock()
        def baa(a: int) -> int:
            return 1

        with dl.DeltaGraph() as g1:
            baa(baa(1))

        with dl.DeltaGraph() as g2:
            baa(baa(2))

        self.assertNotEqual(g1, g2)

    def test_neq_body_name_diff(self):
        @dl.DeltaBlock()
        def foo(a: int) -> int:
            return 1

        @dl.DeltaBlock()
        def baa(a: int) -> int:
            return 1

        with dl.DeltaGraph() as g1:
            baa(baa(1))

        with dl.DeltaGraph() as g2:
            baa(foo(1))

        self.assertNotEqual(g1, g2)

    def test_neq_body_impl_diff(self):
        def get_g1():
            @dl.DeltaBlock()
            def foo(a: int) -> int:
                return 2

            with dl.DeltaGraph() as g1:
                foo(foo(1))
            return g1

        def get_g2():
            @dl.DeltaBlock()
            def foo(a: int) -> int:
                return 1

            with dl.DeltaGraph() as g2:
                foo(foo(1))
            return g2

        self.assertNotEqual(get_g1(), get_g2())

    def test_neq_connectivity_diff(self):
        def get_g1():
            @dl.DeltaBlock()
            def foo(a: int) -> int:
                return 1

            with dl.DeltaGraph() as g1:
                foo(1)
            return g1

        def get_g2():
            @dl.DeltaBlock()
            def foo(a: int) -> int:
                return 1

            with dl.DeltaGraph() as g2:
                foo(foo(1))
            return g2

        self.assertNotEqual(get_g1(), get_g2())


if __name__ == "__main__":
    unittest.main()
