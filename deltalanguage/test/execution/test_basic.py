"""Execute graphs which have nodes with _running_ bodies of all supported
types:

- PyFuncBody
- PyMethodBody
- PyInteractiveBody
- PyMigenBody
- Integration tests
"""

import unittest

import migen

import deltalanguage as dl
from deltalanguage import DeltaRuntimeExit
from deltalanguage.test._graph_lib import (getg_PyFunc_body_graph,
                                           getg_PyInteractiveBody_one_in_one_out,
                                           getg_PyInteractiveBody_one_in_two_out,
                                           getg_PyInteractiveBody_two_in_one_out,
                                           getg_PyInteractiveBody_two_in_two_out)
from deltalanguage.test._node_lib import (add_non_const,
                                          multiplier,
                                          return_2_const,
                                          DUT1,
                                          MigenDUT,
                                          MigenIncrementer,
                                          TripleStateSaver)
from deltalanguage.test.execution.base import TestExecutionBaseDL


@dl.Interactive(inputs=[("num", int)], outputs=[('x', int), ('y', int)])
def add_until_10(node):
    """Sends num on the left port until it is greater than 10, then sends it
    on the right port.
    """
    num = 1
    while num < 10:
        node.send(num, None)
        num = node.receive()["num"]
    node.send(None, num)


@dl.Interactive(inputs=[("num", str)], outputs=[('out', int)], name="blah")
def interactive_func(node):
    node.send(3)
    num = node.receive()["num"]
    num = int(num, base=10)
    node.send(num + 1)


@dl.Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def positional_send(node):
    """Send to multiple outputs via different positional methods
    None, or not specifying enough positions can be used to send nothing.
    """
    node.send(1, 2, False)
    node.send(3, 4)
    node.send(5)
    node.send(6, None)
    node.send(None, None, True)
    node.send(7, None, False)
    node.send(10)


@dl.Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def keyword_send(node):
    """Send to multiple outputs via different keyword methods
    None, or just not specifying a keyword can be used to send nothing.
    """
    node.send(x=1)
    node.send(y=2)
    node.send()
    node.send(z=True)
    node.send(x=3, y=4, z=False)
    node.send(x=5, y=6)
    node.send(x=7, z=False)
    node.send(y=8, z=True)
    node.send(y=None, x=9, z=None)
    node.send(z=False, x=None)
    node.send(x=10)


@dl.Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def positional_and_keyword_send(node):
    """Send to multiple outputs via hybrid positional and keyword methods
    None, or just not specifying a keyword/position can be used to send
    nothing.
    """
    node.send(1, 2, z=False)
    node.send(3, y=4)
    node.send(5, z=True)
    node.send(None, z=False, y=6)
    node.send(None, 7, z=True)
    node.send(8, None, z=False)
    node.send(10, y=None, z=None)


@dl.Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def multiple_specify_kwarg_position_first(node):
    """Specify the same value twice, once by position and once by keyword."""
    node.send(1, x=5)


@dl.Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def multiple_specify_kwarg_position_second(node):
    """Specify the same value twice, once by position and once by keyword
    on not the first value in outputs order.
    """
    node.send(1, 2, y=5)


@dl.Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def too_many_positional(node):
    """Attempt to send too many positional arguments out of a node."""
    node.send(1, 2, False, 3)


@dl.Interactive(outputs=[('x', int), ('y', int), ('z', bool)])
def invalid_kwarg(node):
    """Attempt to send via an invalid keyword."""
    node.send(x=1, foo=7)


@dl.Interactive(outputs=[('inp', int), ('trigger', int)])
def test_bench_no_trigger(node):
    """This node sends 2 consecutive messages, the first is a data signal, the
    second is a trigger to move out of a specific state of the migen FSM.
    """
    node.send(15, 0)
    node.send(0, 1)


@dl.Interactive(outputs=[('inp', int), ('trigger', int)])
def test_bench_yes_trigger(node):
    """This node sends 3 consecutive messages, the first is a data signal, the
    second is the same data signal, and the third is a trigger to move out of
    a specific state of the migen FSM.
    """
    node.send(15, 0)
    # make inp.data available for an extra cycle of migen clock
    node.send(15, 0)
    node.send(0, 1)


class MigenNodeDUT(dl.MigenNodeTemplate):
    """A migen node that accepts a data signal, and a trigger signal that
    moves the FSM out of the "LOADING" state.
    """

    def migen_body(self, template):

        inp = template.add_pa_in_port('inp', dl.Optional(int))
        trigger = template.add_pa_in_port('trigger', dl.Optional(int))
        out = template.add_pa_out_port('out', int)

        # Declare input and output ports always happy to receive/transmit data
        self.comb += (
            inp.ready.eq(1),
            trigger.ready.eq(1),
            out.ready.eq(1),
        )

        commander_fsm = migen.FSM(reset_state="IDLE")
        self.submodules.commander_fsm = commander_fsm

        commander_fsm.act(
            "IDLE",
            migen.If(
                inp.valid == 1,
                migen.NextState("LOADING")
            )
        )

        commander_fsm.act(
            "LOADING",
            migen.If(
                trigger.valid & trigger.data == 1,
                migen.NextState("RETURN")
            ).Else(
                migen.NextValue(out.data, out.data + inp.data),
            )
        )

        commander_fsm.act(
            "RETURN",
            migen.NextValue(out.valid, 1),
            migen.NextState("IDLE")
        )


class AlternatingOutputsMigen(dl.MigenNodeTemplate):
    """
    This node sends a counter value to both output ports
    but only asserts the valid for one at the time
    """

    def migen_body(self, template):
        start = template.add_pa_in_port('start', dl.Optional(int))
        out_a = template.add_pa_out_port('out_a', int)
        out_b = template.add_pa_out_port('out_b', int)
        # This will need to be converted to boolean when migen nodes support
        # boolean
        self.cnt = migen.Signal(10)

        self.comb += (
            out_a.ready.eq(1),
            out_b.ready.eq(1),
            start.ready.eq(1)
        )
        self.sync += migen.If(
            self.cnt & 0x1,
            out_a.valid.eq(start.data),
            out_b.valid.eq(0)
        ).Else(
            out_a.valid.eq(0),
            out_b.valid.eq(start.data)
        )
        self.sync += (
            self.cnt.eq(self.cnt+1),
            out_a.data.eq(self.cnt),
            out_b.data.eq(self.cnt)
        )


class TestExecutionPyFuncBody(TestExecutionBaseDL):
    """Minimal test of nodes with PyFuncBody."""

    def test_PyFuncBody(self):
        graph = getg_PyFunc_body_graph()
        self.check_executes_graph(graph, "saving 5\n")


class TestExecutionPyInteractiveBody(TestExecutionBaseDL):
    """Minimal test of nodes with PyInteractiveBody."""

    def test_PyInteractiveBody_one_in_one_out(self):
        graph = getg_PyInteractiveBody_one_in_one_out()
        self.check_executes_graph(
            graph,
            """\
            received num: 5
            received num: 5
            saving 6
            """
        )

    def test_PyInteractiveBody_one_in_two_out(self):
        graph = getg_PyInteractiveBody_one_in_two_out()

        self.check_executes_graph(
            graph,
            """\
            received num: 4
            received num: 4
            saving 14
            """
        )

    def test_PyInteractiveBody_two_in_one_out(self):
        graph = getg_PyInteractiveBody_two_in_one_out()
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
        graph = getg_PyInteractiveBody_two_in_two_out()

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


class TestExecutionPyInteractiveBodySend(TestExecutionBaseDL):
    """Test the different ways an interactive body can use
    `node.send()` to send values to multiple outputs.
    """

    def test_positional_interactive_send(self):
        ts = TripleStateSaver(11)

        with dl.DeltaGraph() as graph:
            i_send = positional_send.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        self.check_executes_graph(
            graph,
            """\
            [1, 3, 5, 6, 7, 10]
            [2, 4]
            [False, True, False]
            """
        )

    def test_keyword_interactive_send(self):
        ts = TripleStateSaver(15)

        with dl.DeltaGraph() as graph:
            i_send = keyword_send.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        self.check_executes_graph(
            graph,
            """\
            [1, 3, 5, 7, 9, 10]
            [2, 4, 6, 8]
            [True, False, False, True, False]
            """
        )

    def test_keyword_positional_interactive_send(self):
        ts = TripleStateSaver(14)

        with dl.DeltaGraph() as graph:
            i_send = positional_and_keyword_send.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        self.check_executes_graph(
            graph,
            """\
            [1, 3, 5, 8, 10]
            [2, 4, 6, 7]
            [False, True, False, True, False]
            """
        )

    def test_invalid_kwarg(self):
        ts = TripleStateSaver(1)

        with dl.DeltaGraph() as graph:
            i_send = invalid_kwarg.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        self.check_executes_graph(graph, exception=RuntimeError)

    def test_too_many_positional(self):
        ts = TripleStateSaver(1)

        with dl.DeltaGraph() as graph:
            i_send = too_many_positional.call()
            ts.multi_count_print_exit(i_send.x, i_send.y, i_send.z)

        self.check_executes_graph(graph, exception=RuntimeError)

    def test_exception_multi_specify_by_position_and_kwarg1(self):
        saver_x = dl.lib.StateSaver(int)

        with dl.DeltaGraph() as graph:
            i_send = multiple_specify_kwarg_position_first.call()
            saver_x.save_and_exit_if(i_send.x)

        self.check_executes_graph(graph, exception=RuntimeError)

    def test_exception_multi_specify_by_position_and_kwarg2(self):
        saver_x = dl.lib.StateSaver(int, lambda x: x >= 10)
        saver_y = dl.lib.StateSaver(int)

        with dl.DeltaGraph() as graph:
            i_send = multiple_specify_kwarg_position_second.call()
            saver_x.save_and_exit_if(i_send.x)
            saver_y.save(i_send.y)

        self.check_executes_graph(graph, exception=RuntimeError)


class TestExecutionPyMigenBody(TestExecutionBaseDL):
    """Minimal test of nodes with PyMigenBody."""

    def test_PyMigenBody(self):
        s = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph("test_migen_wiring") as graph:
            c1 = DUT1(name='counter1').call(i1=1000)
            c2 = DUT1(name='counter2').call(i1=c1.o1)
            s.save_and_exit(c2.o1)

        self.check_executes_graph(graph, "saving 10\n")

    def test_PyMigenBody_python(self):
        @dl.DeltaBlock(allow_const=False)
        def exit_if_6_else_inc(n: int) -> int:
            print(n)
            if n == 6:
                raise DeltaRuntimeExit
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

    def test_migen_trigger_fails(self):
        """Assert that when the `test_bench_no_trigger` node sends data, the
        output of the migen node is 0 due to the data not loading into output
        signal properly.
        """
        s = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph() as graph:
            test_bench_output = test_bench_no_trigger.call()
            c1 = MigenNodeDUT().call(
                inp=test_bench_output.inp,
                trigger=test_bench_output.trigger
            )
            s.save_and_exit(c1.out)

        self.check_executes_graph(graph, "saving 0\n")

    def test_migen_trigger_succeeds(self):
        """Assert that when the `test_bench_ye_trigger` node sends data, the
        output of the migen node is 15 since the data signal is available on the
        particular clock cycle that loads in the data.
        """
        s = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph() as graph:
            test_bench_output = test_bench_yes_trigger.call()
            c1 = MigenNodeDUT().call(
                inp=test_bench_output.inp,
                trigger=test_bench_output.trigger
            )
            s.save_and_exit(c1.out)

        self.check_executes_graph(graph, "saving 15\n")

    def test_one_migen_node_with_2_outs(self):
        """One PyMigenBody with 2 out ports produces what we expect."""
        s = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph() as graph:
            counter = MigenDUT().call(40, 2)
            s.save_and_exit(add_non_const(counter.out1,
                                          multiplier(counter.out2)))

        self.check_executes_graph(graph, "saving 5042\n")

    def test_one_migen_node_with_separate_ctrl_on_output_valid(self):
        """One PyMigenBody with 2 optional output ports produces
        the correct valid values (for the different ports).
        The migen node should be generating a sequence of outputs
        (1, None), (None, 2), (3, None) etc... """
        checker = dl.lib.StateSaver(int, condition=lambda x: x==3, verbose=True)
        
        with dl.DeltaGraph() as graph:
            alt = AlternatingOutputsMigen().call(1)
            my_adder = add_non_const(alt.out_a, alt.out_b)
            # Checking that we have received a 1 and a 2
            checker.save_and_exit_if(my_adder)

        self.check_executes_graph(graph, "saving 3\n")


class TestExecutionGeneral(TestExecutionBaseDL):
    """Run example graphs with nodes's bodies of all types."""

    def test_exception_catching(self):
        """Any exception besides DeltaRuntimeExit raised in a node
        should raise a universally identifiable error,
        such as RuntimeError.
        """
        @dl.DeltaBlock(allow_const=False)
        def raise_exception(n: int):
            raise Exception

        with dl.DeltaGraph() as graph:
            raise_exception(666)

        self.check_executes_graph(graph, exception=RuntimeError)

    def test_integration(self):
        """Constructs the following graph:
        +---------------------------+
        |             SAVE          |
        |   +-----+    ^            |
        +--->Add  +----+            |
            |to 10|        +----+   |
            |     +-------->    |   |
            +-----+        |ADD +---+
                     2 --->|    |
                           +----+
        """
        s = dl.lib.StateSaver(int, verbose=True)

        with dl.DeltaGraph() as graph:
            add_ph = dl.placeholder_node_factory()
            b = return_2_const()
            int_node = add_until_10.call(num=add_ph)
            add_node = add_non_const(b, int_node.x)
            add_ph.specify_by_node(add_node)
            s.save_and_exit(int_node.y)

        self.check_executes_graph(graph, "saving 11\n")


if __name__ == "__main__":
    unittest.main()
