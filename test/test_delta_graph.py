"""Test of DeltaGraph class."""

from typing import OrderedDict
import unittest

import deltalanguage as dl

from test._utils import return_1, TwoIntsT, TwoInts


@dl.DeltaBlock()
def union_one_receiver(x: dl.DUnion([int])) -> int:
    return x


ForkedReturnT, ForkedReturn = dl.make_forked_return({
    'a': int, 'b': bool, 'c': int, 'd': int
})


@dl.DeltaBlock()
def forked_return_output(x: dl.DInt(dl.DSize(8)), y: dl.DInt(dl.DSize(8))) -> ForkedReturnT:
    return ForkedReturn(a=0, b=1, c=1, d=0)


@dl.DeltaBlock()
def forked_return_output_no_input() -> ForkedReturnT:
    return ForkedReturn(a=0, b=1, c=1, d=0)


@dl.DeltaBlock(allow_const=False)
def multi_body_no_output(i: dl.DInt(dl.DSize(8))) -> dl.Void:
    print(i)


class Foo():

    def __init__(self):
        pass

    @dl.DeltaMethodBlock()
    def method_func_no_output(self, i: dl.DInt(dl.DSize(8))) -> dl.Void:
        print(i + 1)


class MigenFoo(dl.MigenNodeTemplate):
    def migen_body(self, template):
        template.add_pa_in_port('i', dl.DOptional(dl.DInt(dl.DSize(8))))


@dl.Interactive({'i': dl.DInt(dl.DSize(8))}, out_type=dl.Void)
def interactive_func_no_output(node: dl.RealNode):
    a = node.receive('i')


template_no_output_no_body = dl.NodeTemplate(
    name="template_no_output_no_body",
    in_params=OrderedDict([('i', dl.DInt(dl.DSize(8)))]),
    out_type=dl.Void
)


@dl.DeltaBlock()
def experiment_stopper(completed: dl.DInt(dl.DSize(8))) -> dl.Void:
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
        def test_node(a: dl.DOptional(int)) -> dl.Void:
            pass

        with dl.DeltaGraph() as graph:
            p = dl.placeholder_node_factory()
            test_node(p)

        self.assertTrue(graph.check())


def to_union_of_one(node: dl.RealNode) -> dl.RealNode:
    org_t = node.out_type
    node.out_type = dl.DUnion([org_t])

    return node


class DeltaGraphStrTest(unittest.TestCase):
    """Test for correct graph printing."""

    def test_graph_str_output(self):
        """Stringify a pre-defined graph and compare output to test data"""

        dl.DeltaGraph.clean_stack()

        with dl.DeltaGraph() as graph:
            n1 = forked_return_output(1, 2)
            n2 = template_no_output_no_body.call(n1.a)
            n3 = multi_body_no_output(n1.b)
            n4 = MigenFoo().call(i=n1.d)
            n5 = experiment_stopper(n1.c)

        obj = Foo()
        n3.add_body(obj.method_func_no_output)
        n3.add_body(interactive_func_no_output)

        with open('test/data/graph_str.txt', 'r') as file:
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
        @dl.Interactive({'a': int}, dl.Void)
        def foo(node):
            node.receive("a")

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo.call(b=1)

    def test_MigenNodeTemplate(self):
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', dl.DOptional(int))

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
        @dl.Interactive({"a": int}, dl.Void)
        def foo(node):
            print(node.receive("a"))

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo.call(a=foo.call(a=1))

    def test_MigenNodeTemplate(self):
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', dl.DOptional(int))

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                AMigenNode().call(a=AMigenNode().call(a=1))


class DeltaGraphWiringWrongOutputTest(unittest.TestCase):
    """Error is raised when trying to get an output from a node with multiple
    output ports, but use a wrong port name.
    """

    def test_DeltaBlock(self):
        @dl.DeltaBlock()
        def foo(a: int) -> TwoIntsT:
            return TwoInts(x=1, y=2)

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo(foo(1).z)

    def test_DeltaMethodBlock(self):
        class AClass:

            @dl.DeltaMethodBlock()
            def foo(self, a: int) -> TwoIntsT:
                return TwoInts(x=1, y=2)

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                AClass().foo(AClass().foo(1).z)

    def test_Interactive(self):
        @dl.Interactive({"a": int}, TwoIntsT)
        def foo(node):
            node.send(TwoInts(x=1, y=2))

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                foo.call(a=foo.call(a=1).z)

    def test_MigenNodeTemplate(self):
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', dl.DOptional(int))
                template.add_pa_out_port('x', int)
                template.add_pa_out_port('y', int)

        with self.assertRaises(dl.data_types.DeltaIOError):
            with dl.DeltaGraph():
                AMigenNode().call(a=AMigenNode().call(a=1).z)


if __name__ == "__main__":
    unittest.main()
