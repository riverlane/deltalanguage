from math import log2, ceil, trunc
import numpy as np
import logging
import random
import time
import sys

from migen import If, Signal, FSM, NextState, NextValue, Array, Cat

import deltalanguage as dl

from core_unit import CoreUnit
from commands import Commands


""" Parameters
Can be any unsignefd integer value such that :
[C_VECTOR_LEN = C_N_BITS x C_N_INPUTS] <= 64

"""
C_VECTOR_LEN = 64  # MAX 64
C_N_BITS = 8  # MAX 64
C_N_INPUTS = 8  # MAX 64


class CombTree(dl.MigenNodeTemplate):
    """Generates resources to compute given operation according to input size.

    Generic constants:
     - N_BITS: data bit-width
     - N_INPUTS: number of matrix elements to operate on

    Inputs:
     - d_in: array of data elements [NBITS x NBINPUTS]
     - cmd: the type of operation to be performed

    Outputs:
     - d_out: result [NBITS x 1] single value

    Supported commands:
     - min(): 0x01
     - max(): 0x02
     - sum(): 0x03
     - mean(): 0x04
    """

    def migen_body(self, template):

        # generics
        N_BITS = template.generics["N_BITS"]  # 1-64
        N_INPUTS = template.generics["N_INPUTS"]
        TREE_DEPTH = int(ceil(log2(N_INPUTS)))

        # inputs
        self.d_in = template.add_pa_in_port(
            'd_in', dl.Optional(dl.Int(dl.Size(N_BITS*N_INPUTS))))
        self.cmd = template.add_pa_in_port('cmd', dl.Optional(dl.Int()))

        # outputs
        self.d_out = template.add_pa_out_port('d_out', dl.Int())
        self.err = template.add_pa_out_port('error', dl.Int())

        # input length correction [need a power of 2 sized tree]
        N_INPUTS_CORR = pow(2, TREE_DEPTH)

        # internals

        # correct the size of the input tree to be a power of 2
        # and register the inputs
        self.d_in_full_reg = Signal(N_INPUTS_CORR*N_BITS)
        self.d_in_valid_reg = Signal(1)
        self.cmd_data_reg = Signal(8)
        self.cmd_valid_reg = Signal(1)

        # register outputs
        self.d_out_data_reg = Signal(N_BITS+TREE_DEPTH)
        self.d_out_valid_reg = Signal(1)
        self.err_data_reg = Signal(1)
        self.err_valid_reg = Signal(1)

        # create the 2D array of data [INPUTS x TREE_DEPTH] to route
        # all the core units in an iterative way. The number of bits is incremented
        # at each stage to account for the carry in additions.
        self.d_pipe = Array(Array(Signal(N_BITS+b) for a in range(N_INPUTS_CORR))
                            for b in range(TREE_DEPTH+1))

        # create the 2D array of error signals.
        self.e_pipe = Array(Array(Signal(N_BITS) for a in range(N_INPUTS_CORR))
                            for b in range(TREE_DEPTH))

        ###

        # correct input vector length to match a power of 2.
        # fill non-provided inputs with 0's (affects mean and minimum)
        self.sync += [
            self.d_in_full_reg.eq(self.d_in.data),
            self.d_in_valid_reg.eq(self.d_in.valid),
            self.cmd_data_reg.eq(self.cmd.data),
            self.cmd_valid_reg.eq(self.cmd.valid)
        ]

        # wiring inputs to the first stage of the tree
        for i in range(N_INPUTS_CORR):
            self.comb += [
                self.d_pipe[0][i].eq(self.d_in_full_reg[N_BITS*i:N_BITS*(i+1)])
            ]

        # instantiation of the core units.
        for j in range(TREE_DEPTH):
            for i in range(int(N_INPUTS_CORR/(pow(2, j+1)))):
                self.submodules += CoreUnit(self.d_pipe[j][2*i],
                                            self.d_pipe[j][2*i+1],
                                            self.d_pipe[j+1][i],
                                            self.cmd_data_reg,
                                            self.e_pipe[j][i],
                                            N_BITS)

                # error signal propagation. If any of the single units have
                # a high error signal, the error is propagated to the node's output.
                self.comb += [
                    If(
                        self.e_pipe[j][i] == 1,
                        self.err_data_reg.eq(1)
                    )
                ]

        self.comb += [
            self.d_in.ready.eq(1),
            self.cmd.ready.eq(1),
            self.d_out_data_reg.eq(self.d_pipe[TREE_DEPTH][0]),
            If(
                self.d_in_valid_reg,
                self.err_valid_reg.eq(1),
                self.d_out_valid_reg.eq(1)
            ).Else(
                self.err_valid_reg.eq(0)
            )
        ]

        self.sync += [
            self.d_out.data.eq(self.d_out_data_reg),
            self.d_out.valid.eq(self.d_out_valid_reg),
            self.err.data.eq(self.err_data_reg),
            self.err.valid.eq(self.err_valid_reg)
        ]


def generate_data_vector(N_BITS, N_INPUTS):
    return np.random.randint(0, pow(2, N_BITS), size=N_INPUTS)


@dl.Interactive(inputs=[('result', dl.Int()), ('error', dl.Int())],
                outputs=[('cmd', dl.Int()),
                         ('data', dl.Int(dl.Size(C_VECTOR_LEN)))])
def testbench(node):

    data_array = generate_data_vector(C_N_BITS, C_N_INPUTS)
    # Temporary - needs df.Array => migen.Array support
    data_vector = 0
    logging.debug(f'data sent to DUT {data_array}')
    for i in range(C_N_INPUTS):
        data_vector += data_array[i] << C_N_BITS*i

    data_vector = dl.Int(dl.Size(C_VECTOR_LEN)
                          ).from_numpy_object(data_vector)

    for cmd in range(0x01, 0x06):
        node.send(data=data_vector, cmd=cmd)
        result = node.receive('result')
        error = node.receive('error')
        logging.debug(f'cmd: {cmd}')
        exp_err = 0
        if cmd == Commands.MIN:
            exp_res = np.min(data_array)
            logging.debug(f'result: {result}, expected: {exp_res}')
            assert result == exp_res
        elif cmd == Commands.MAX:
            exp_res = np.max(data_array)
            logging.debug(f'result: {result}, expected: {exp_res}')
            assert result == exp_res
        elif cmd == Commands.SUM:
            exp_res = np.sum(data_array)
            logging.debug(f'result: {result}, expected: {exp_res}')
            assert result == exp_res
        elif cmd == Commands.AVG:
            exp_res_low = trunc(np.mean(data_array))-1
            exp_res_high = int(np.mean(data_array))+1
            exp_res = np.mean(data_array)
            logging.debug(f'result: {result}, expected: {exp_res}')
            assert result >= exp_res_low
            assert result <= exp_res_high
        else:
            exp_err = 1
            result = -1
            exp_res = -1
        assert error == exp_err

    raise dl.DeltaRuntimeExit


if __name__ == "__main__":

    logging.root.setLevel(logging.DEBUG)

    with dl.DeltaGraph() as graph:

        # define placeholders
        p0_tb = dl.placeholder_node_factory()

        # DUT
        dut = CombTree(
            name='comb_tree',
            vcd_name='comb_tree.vcd',
            lvl=logging.ERROR,
            generics={
                "N_BITS": C_N_BITS,
                "N_INPUTS": C_N_INPUTS
            }
        ).call(
            d_in=p0_tb.data,
            cmd=p0_tb.cmd
        )

        # testbench
        tb = testbench.call(
            result=dut.d_out,
            error=dut.error,
            N_BITS=C_N_BITS,
            N_INPUTS=C_N_INPUTS
        )

        # route placeholders
        p0_tb.specify_by_node(tb)

    # run graph
    print(graph)
    rt = dl.DeltaPySimulator(graph)
    rt.run()
