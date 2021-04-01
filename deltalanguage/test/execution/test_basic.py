"""Execute graphs which have nodes with _running_ bodies of all supported
types:

- PyFuncBody
- PyMethodBody
- PyInteractiveBody (TODO move test_interactive_node.py)
- PyMigenBody (TODO collect duplicating tests from all over the place,
  test_migen_interactive_comms.py, test_migen_node.py, etc.)
- TODO move tests from test_runtime.py
"""

import unittest

import deltalanguage as dl

from deltalanguage.test._utils import add_non_const, DUT1, MigenIncrementer
from deltalanguage.test.execution.base import TestExecutionBaseDL, PYSIMULATOR


class TestExecutionBasic(TestExecutionBaseDL):
    """Run example graphs with nodes's bodies of all types."""

    def test_PyFuncBody(self):
        s = dl.lib.StateSaver(int, verbose=True)
        with dl.DeltaGraph() as graph:
            s.save_and_exit(add_non_const(2, 3))

        self.check_executes_graph(graph, "saving 5\n")

    def test_PyInteractiveBody_one_in_one_out(self):
        @dl.Interactive([("num", int)], [("output", int)])
        def interactive_func(node: dl.PythonNode):
            for _ in range(2):
                num = node.receive("num")
                print(f"received num: {num}")
            node.send(num + 1)

        s = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph() as graph:
            s.save_and_exit(interactive_func.call(add_non_const(2, 3)))

        self.check_executes_graph(
            graph,
            """\
            received num: 5
            received num: 5
            saving 6
            """)

    def test_PyInteractiveBody_one_in_two_out(self):
        @dl.Interactive(
            [("num", dl.Int(dl.Size(32)))],
            [('num_out', dl.Int(dl.Size(32))), ('val_out', dl.Bool())]
        )
        def interactive_func(node: dl.PythonNode):
            for _ in range(2):
                num = node.receive("num")
                print(f"received num: {num}")
            node.send(num_out=None, val_out=False)
            node.send(num_out=14, val_out=False)

        s0 = dl.lib.StateSaver(bool, condition=lambda x: x)
        s1 = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph() as graph:
            int_func = interactive_func.call(num=4, opt_val=True)
            s0.save_and_exit_if(int_func.val_out)
            s1.save_and_exit(int_func.num_out)

        self.check_executes_graph(
            graph,
            """\
            received num: 4
            received num: 4
            saving 14
            """
        )

    def test_PyInteractiveBody_two_in_one_out(self):
        @dl.Interactive([("num", dl.Int(dl.Size(32))),
                         ("opt_val", dl.Optional(dl.Bool()))],
                        [("output", dl.Bool())])
        def interactive_func(node: dl.PythonNode):
            for _ in range(2):
                num = node.receive("num")
                opt_val = node.receive("opt_val")
                print(f"received opt_val: {opt_val}")
                print(f"received num: {num}")
            node.send(True)

        s = dl.lib.StateSaver(bool, verbose=True, condition=lambda x: x)

        with dl.DeltaGraph() as graph:
            int_func = interactive_func.call(num=4, opt_val=True)
            s.save_and_exit_if(int_func)

        self.check_executes_graph(
            graph,
            """\
            received opt_val: True
            received num: 4
            received opt_val: True
            received num: 4
            saving True
            """
        )

    def test_PyInteractiveBody_two_in_two_out(self):
        @dl.Interactive(
            [("num", dl.Int(dl.Size(32))),
             ("opt_val", dl.Optional(dl.Bool()))],
            [('num_out', dl.Int(dl.Size(32))),
             ('val_out', dl.Bool())]
        )
        def interactive_func(node: dl.PythonNode):
            for _ in range(2):
                num = node.receive("num")
                opt_val = node.receive("opt_val")
                print(f"received opt_val: {opt_val}")
                print(f"received num: {num}")
            node.send(num_out=None, val_out=False)
            node.send(num_out=14, val_out=False)

        s0 = dl.lib.StateSaver(bool, condition=lambda x: x)
        s1 = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph() as graph:
            int_func = interactive_func.call(num=4, opt_val=True)
            s0.save_and_exit_if(int_func.val_out)
            s1.save_and_exit(int_func.num_out)

        self.check_executes_graph(
            graph,
            """\
            received opt_val: True
            received num: 4
            received opt_val: True
            received num: 4
            saving 14
            """
        )

    def test_PyMigenBody(self):
        s = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph("test_migen_wiring") as graph:
            c1 = DUT1(name='counter1').call(i1=1000)
            c2 = DUT1(name='counter2').call(i1=c1.o1)
            s.save_and_exit(c2.o1)

        # FIXME this test's output changes:
        # `saving 10` via DeltaPySimulator and
        # `saving 1020` via Deltasimulator
        if PYSIMULATOR:
            self.check_executes_graph(graph, "saving 10\n")
        else:
            self.check_executes_graph(graph, "saving 1020\n")

    def test_PyMigenBody_python(self):
        @dl.DeltaBlock(allow_const=False)
        def exit_if_6_else_inc(n: int) -> int:
            print(n)
            if n == 6:
                raise dl.DeltaRuntimeExit
            else:
                return n+1

        with dl.DeltaGraph() as graph:
            ph = dl.placeholder_node_factory()
            c1 = MigenIncrementer().call(i1=ph)
            ex = exit_if_6_else_inc(c1.o1)
            ph.specify_by_node(ex)

        self.check_executes_graph(
            graph,
            """\
            0
            2
            4
            6
            """
        )


if __name__ == "__main__":
    unittest.main()
