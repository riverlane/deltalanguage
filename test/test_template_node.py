import unittest

from deltalanguage.data_types import (DBool,
                                      DInt,
                                      Void,
                                      make_forked_return)
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  ForkedNode,
                                  placeholder_node_factory,
                                  template_node_factory)


class TemplateNodeTest(unittest.TestCase):

    def setUp(self):
        def add_standalone(a: int, b: int) -> int:
            return a + b

        self.add_standalone = add_standalone

        @DeltaBlock(allow_const=True)
        def add_const(a: int, b: int) -> int:
            return a + b

        @DeltaBlock(allow_const=False)
        def add_nonconst(a: int, b: int) -> int:
            return a + b

        @DeltaBlock(allow_const=False)
        def print_then_exit(to_print: object) -> Void:
            self.output = to_print
            raise DeltaRuntimeExit

        with DeltaGraph() as self.test_graph_inline:
            self.n_standalone = template_node_factory(
                a=1, b=2, out_type=int)
            print_then_exit(to_print=self.n_standalone)

        with DeltaGraph() as self.test_graph_const_in:
            a_1 = add_const(1, 2)
            a_2 = add_const(3, 4)
            self.n_const = template_node_factory(a=a_1, b=a_2, out_type=int)
            print_then_exit(to_print=self.n_const)

        with DeltaGraph() as self.test_graph_nonconst_in:
            a_1 = add_nonconst(1, 2)
            a_2 = add_nonconst(3, 4)
            self.n_nonconst = template_node_factory(a=a_1,
                                                    b=a_2,
                                                    out_type=int)
            print_then_exit(to_print=self.n_nonconst)

    def test_add_standalone_const_func(self):
        self.n_standalone.specify_by_func(self.add_standalone,
                                          allow_const=True)
        rt = DeltaPySimulator(self.test_graph_inline)
        rt.run()
        self.assertEqual(self.output, 3)

    def test_add_const_in_const_func(self):
        self.n_const.specify_by_func(self.add_standalone, allow_const=True)
        rt = DeltaPySimulator(self.test_graph_const_in)
        rt.run()
        self.assertEqual(self.output, 10)

    def test_add_nonconst_in_const_func(self):
        self.n_nonconst.specify_by_func(self.add_standalone, allow_const=True)
        rt = DeltaPySimulator(self.test_graph_nonconst_in)
        rt.run()
        self.assertEqual(self.output, 10)

    def test_add_standalone_nonconst_func(self):
        self.n_standalone.specify_by_func(self.add_standalone,
                                          allow_const=False)
        rt = DeltaPySimulator(self.test_graph_inline)
        rt.run()
        self.assertEqual(self.output, 3)

    def test_add_const_in_nonconst_func(self):
        self.n_const.specify_by_func(self.add_standalone,
                                     allow_const=False)
        rt = DeltaPySimulator(self.test_graph_const_in)
        rt.run()
        self.assertEqual(self.output, 10)

    def test_add_nonconst_in_nonconst_func(self):
        self.n_nonconst.specify_by_func(self.add_standalone, allow_const=False)
        rt = DeltaPySimulator(self.test_graph_nonconst_in)
        rt.run()
        self.assertEqual(self.output, 10)

    def test_forked_input(self):
        ForkedReturnT, ForkedReturn = make_forked_return({'a': int, 'b': bool})

        @DeltaBlock()
        def add_1_true(n: int) -> ForkedReturnT:
            return ForkedReturn(a=n+1, b=True)
        with DeltaGraph() as _test_graph:
            forked_input = add_1_true(n=5)
            template = template_node_factory(
                a=forked_input.a, b=forked_input.b, out_type=Void)
        body_input = template.body.kw_in_nodes['a']
        self.assertEqual(
            body_input.out_type.elem_dict[body_input.index] if isinstance(
                body_input, ForkedNode
            ) else body_input.out_type,
            DInt()
        )
        body_input = template.body.kw_in_nodes['b']
        self.assertEqual(
            body_input.out_type.elem_dict[body_input.index] if isinstance(
                body_input, ForkedNode
            ) else body_input.out_type,
            DBool()
        )

    def test_placeholder_input_raises_exception(self):
        with self.assertRaises(TypeError):
            with DeltaGraph():
                template_node_factory(
                    a=placeholder_node_factory(), out_type=Void)

    def test_placeholder_input_no_exception(self):
        with DeltaGraph():
            template = template_node_factory(
                a=placeholder_node_factory(), out_type=Void, arg_types={'a': int})

        body_input = template.body.kw_in_nodes['a']
        self.assertEqual(
            body_input.out_type.elem_dict[body_input.index] if isinstance(
                body_input.out_type, ForkedNode
            ) else body_input.out_type,
            DInt()
        )

    def test_partial_arg_types(self):
        @DeltaBlock()
        def bool_and(a: bool, b: bool) -> bool:
            return a and b
        with DeltaGraph():
            template = template_node_factory(a=placeholder_node_factory(),
                                             b=bool_and(a=True, b=False),
                                             out_type=Void,
                                             arg_types={'a': int})

        body_input = template.body.kw_in_nodes['a']
        self.assertEqual(
            body_input.out_type.elem_dict[body_input.index] if isinstance(
                body_input, ForkedNode
            ) else body_input.out_type,
            DInt()
        )
        body_input = template.body.kw_in_nodes['b']
        self.assertEqual(
            body_input.out_type.elem_dict[body_input.index] if isinstance(
                body_input, ForkedNode
            ) else body_input.out_type,
            DBool()
        )

    def test_template_input_raises_exception(self):
        @DeltaBlock()
        def add(a: int, b: int) -> int:
            return a+b
        with self.assertRaises(TypeError):
            with DeltaGraph():
                template_node_factory(
                    a=add(a=1, b=2), arg_types={'a': bool}, out_type=Void)


if __name__ == "__main__":
    unittest.main()
