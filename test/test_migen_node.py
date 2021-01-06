"""Testing nodes with migen, a.k.a. PyMigenNodes."""

import io
import json
import logging
import unittest
import unittest.mock

from test._utils import InputCheckerWithExit, add_non_const

import dill
import migen

from deltalanguage.data_types import BaseDeltaType, DOptional
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import (DeltaPySimulator,
                                   deserialize_graph,
                                   serialize_graph)
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  MigenNodeTemplate,
                                  PythonBody)

from examples.tutorials.migen_hardware_examples import (
    generate_graph_constant_input,
    generate_graph_interactive_input
)


class AlternatingOutputsMigen(MigenNodeTemplate):
    """
    This node sends a counter value to both output ports
    but only asserts the valid for one at the time
    """

    def migen_body(self, template):
        start = template.add_pa_in_port('start', DOptional(int))
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


@DeltaBlock(allow_const=False)
def adder(a: int, b: int) -> int:
    return a + b


@DeltaBlock(allow_const=False)
def multiplier(a: int) -> int:
    return a*1000


class TestMigen(MigenNodeTemplate):
    """Example class should subclass MigenNodeTemplate and define migen_body.
    """

    def migen_body(self, template):
        # Input/Outputs start here:

        # 2 inputs and 2 outputs.
        #
        # This block group ports which will be accessed by migen, using
        # the protocol adapters.
        # in_ports and out_ports implement a similar logic based on 3
        # signals, ready, valid and data.
        # An input can be received when the ready signal is = '1'.
        # data contains the value of the message that we are receiving
        # and can considered sensible only when valid = '1', i.e. when
        # a new data has been received on the pa_input_port.
        # The opposite logic holds true for the outputs.
        in1 = template.add_pa_in_port('in1', DOptional(int))
        in2 = template.add_pa_in_port('in2', DOptional(int))
        out1 = template.add_pa_out_port('out1', int)
        out2 = template.add_pa_out_port('out2', int)

        # The main migen logic starts here:

        # Everything below is just an example that show different routines.

        # Add a 32-bit counter (0-2**32-1) which will increment at each clock
        # cycle.
        self.counter = migen.Signal(32)
        self.sync += self.counter.eq(self.counter + 1)

        # Add a condition when in_ports are ready.
        self.comb += migen.If(
            self.counter >= 3,
            in1.ready.eq(1),
            in2.ready.eq(1)
        )

        # Pretend that we do a useful calculations.
        # Here we first check that the outputs are ready.
        # Then wait for the counter to reach 100.
        # And write outputs.
        # Note that the output should be marked as valid.
        self.comb += migen.If(
            (out1.ready & out2.ready) == 1,
            migen.If(
                self.counter == 5,
                out1.data.eq(in1.data + in2.data),
                out2.data.eq(self.counter),
                out1.valid.eq(in1.valid & in2.valid),
                out2.valid.eq(in1.valid & in2.valid)
            ).Else(
                out1.valid.eq(0),
                out2.valid.eq(0)
            )
        )


class MigenNodeSerialisationTest(unittest.TestCase):

    def setUp(self):
        DeltaGraph.clean_stack()

    def test_serialisation(self):
        """Serialize/deserialize a graph with a PyMigenNode.

        Notes
        -----
        The content of the bodies depends on the environment, i.e. how the test
        is executed. For this reason we just compare the structure of the graph
        here.
        """
        s = StateSaver(int)

        example_migen = TestMigen(tb_num_iter=2000,
                                  name='counter',
                                  lvl=logging.INFO,
                                  vcd_name="/workdir/TestMigen.vcd")

        with DeltaGraph() as graph:
            example_migen_out = example_migen.call(in1=40, in2=2)
            s.save_and_exit(adder(example_migen_out.out1,
                                  multiplier(example_migen_out.out2)))

        data, _ = serialize_graph(graph)
        self.assertEqual(type(data), bytes)
        g_capnp = deserialize_graph(data).to_dict()
        for body in g_capnp['bodies']:
            if 'python' in body:
                self.assertTrue(isinstance(dill.loads(
                    body['python']['dillImpl']), PythonBody))
                del body['python']['dillImpl']
        for node in g_capnp['nodes']:
            for port in node['inPorts'] + node['outPorts']:
                self.assertTrue(isinstance(
                    dill.loads(port['type']), BaseDeltaType))
                del port['type']
        with open('test/data/graph_with_migen_capnp.json', 'r') as file:
            self.assertEqual(g_capnp, json.load(file))

    def test_one_migen_node_with_2_outs(self):
        """One PyMigenNode with 2 out ports produces what we expect."""
        s = StateSaver(int, verbose=True)

        with DeltaGraph() as graph:
            counter = TestMigen(tb_num_iter=2000,
                                name='counter',
                                lvl=logging.INFO).call(in1=40, in2=2)
            s.save_and_exit(adder(counter.out1, multiplier(counter.out2)))

        rt = DeltaPySimulator(graph)
        rt.run()

        self.assertEqual(s.saved, [5042])

    def test_one_migen_node_with_separate_ctrl_on_output_valid(self):
        """One PyMigenNode with 2 optional output ports produces
        the correct valid values (for the different ports).
        The migen node should be generating a sequence of outputs
        (1, None), (None, 2), (3, None) etc... """
        with DeltaGraph() as graph:
            alt = AlternatingOutputsMigen(tb_num_iter=100,
                                          name='alternatingOutput',
                                          lvl=logging.INFO).call(start=1)
            my_adder = add_non_const(alt.out_a, alt.out_b)
            # Checking that we have received a 1 and a 2
            checker = InputCheckerWithExit(lambda x: (x == 3))
            checker.check(my_adder)

        rt = DeltaPySimulator(graph)
        rt.run()

        self.assertEqual(checker.cond_met, True)


class MigenNodeHardwareBlocksTest(unittest.TestCase):

    def setUp(self):
        DeltaGraph.clean_stack()

    @unittest.mock.patch('sys.stdout', new_callable=io.StringIO)
    def test_migen_node_reset_shaper_constant(self, mock_stdout):
        """One PyMigenNode that takes as input a reset signal and extends the
        length of the reset to N clock cycles reset.
        """
        graph, _ = generate_graph_constant_input()
        rt = DeltaPySimulator(graph)
        rt.run()
        self.assertEqual(
            mock_stdout.getvalue(),
            'CHECK_SHAPE: reset has lasted at least 5 clk cycles\n'
        )

    @unittest.mock.patch('sys.stdout', new_callable=io.StringIO)
    def test_migen_node_reset_shaper_pulse(self, mock_stdout):
        """One PyMigenNode that takes as input a reset signal and extends the
        length of the reset to N clock cycles reset. We generate a pulse of
        length 1 clock cycle (i.e. 0010) and check for (00000...111110)
        """

        graph, _ = generate_graph_interactive_input(verbose=False)
        rt = DeltaPySimulator(graph)
        rt.run()
        self.assertEqual(mock_stdout.getvalue(),
                         'CHECK_SHAPE: reset has lasted exactly 5 clk cycles\n')


if __name__ == "__main__":
    unittest.main()
