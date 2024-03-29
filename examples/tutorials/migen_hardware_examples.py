import logging

import migen

import deltalanguage as dl


class LengthChecker:
    """The LengthChecker block verifies that we have received a sequence
    of n reset signals (rst=1). If the argument interactive is set
    to True, it also checks that the reset returns to a de-asserted
    (rst=0) state.
    """

    def __init__(self, ticks, interactive=False, verbose=False):
        self.length = 0
        self.ticks = ticks
        self.interactive = interactive
        self.verbose = verbose

    @dl.DeltaMethodBlock()
    def check_shape(self, rst: int) -> bool:
        self.length += rst
        if self.verbose:
            print(f"CHECK_SHAPE: received rst {rst}")

        if self.length == self.ticks:
            msg = "CHECK_SHAPE: reset has lasted"
            if self.interactive:
                if rst == 0:
                    print(f"{msg} exactly {self.length} clk cycles")
                    assert self.length == 5
                    raise dl.DeltaRuntimeExit
            else:
                print(f"{msg} at least {self.length} clk cycles")
                assert self.length == 5
                raise dl.DeltaRuntimeExit

        return True


@dl.Interactive([("status", bool)], [('output', int)])
def one_shot_run(node):
    """Sends a simple pulse 010 and then sits and waits.

    We are using an interactive node because we want to simulate a network-like
    communication. The 0 and 1 can be seen as out_of_reset and enter_reset that
    the hardware (HwResetShaper) block will have to convert to an internally
    viable representation.
    """
    verbose = False
    sequence = [0, 1, 0]
    cnt = 0
    for s in sequence:
        node.send(s)
        if verbose:
            print(f"one_shot_run: [@{cnt}] sending -> {s} ")
        st = node.receive('status')
        cnt = cnt + 1
        if verbose:
            print(f"one_shot_run: [@{cnt}] received ")
    while(True):
        st = node.receive('status')
        if verbose:
            print(f"one_shot_run: [@{cnt}] received!")


class HwResetShaper(dl.MigenNodeTemplate):
    """A reset shaper extends a single clock reset to last n clock cycles.
    Handy for guarantying proper completion/propagation of a reset signal
    throughout the design.
         _                 ________
    ____| |__  =>  _______|        |______
    """

    def migen_body(self, template):
        # We are using a Optional here because the code should run
        # no matter the input. If you were to use an int (so a
        # not-optional input) we would stall the migen simulation until
        # an input is received. In this example, we have a cyclical graph
        # in which the hardware node (migenNode) must produce an output
        # (a reset signal) no matter the input.
        pulse_in = template.add_pa_in_port('pulse_in', dl.Optional(int))
        reset_out = template.add_pa_out_port('reset_out', int)

        # Constants
        self.NUM_CLOCKS = 5
        # We set the lowest NUM_CLOCKS bits of INIT_VAL to be '1's
        self.INIT_VAL = 2**self.NUM_CLOCKS-1

        # Signal that generates a pulse of length NUM_CLOCKS
        self.shaper = migen.Signal(self.NUM_CLOCKS+1)

        # When I receive a reset signal -> initialise the shaper to contain
        # N '1's.
        # If I haven't received one just shift the value to the left
        # 01111 -> 00111. I will use the lowest bit for the reset_out signal
        # This equates to seconding N times a '1' after receiving a pulse_in
        # followed by '0'. Note: the sync construct instructs migen that the
        # logic contained within the block is sequential - i.e. it can only
        # change on a clock transaction (from low to high).
        self.sync += (
            migen.If(
                (pulse_in.valid == 1) & (pulse_in.data == 1),
                self.shaper.eq(self.INIT_VAL)
            ).Else(
                self.shaper.eq(self.shaper >> 1)
            )
        )

        # Always generating an output
        self.sync += (reset_out.data.eq(self.shaper[0]))

        # Always ready to receive a reset, always generating an output.
        # Note: comb (combinatorial logic) is executed instantaneously
        # when inputs change. In this example, inputs for the
        # reset_out.valid is a constant 1 so it is always = 1.
        # If it was a signal the value of reset_out.valid would change
        # together with the input signal.
        self.comb += (reset_out.valid.eq(1),
                      pulse_in.ready.eq(1),
                      reset_out.ready.eq(1))


def generate_graph_constant_input():
    """This function returns an acyclic graph:

    Constant -> HwResetShaper -> LengthChecker.
    Limitations: the HwResetShaper will always receive a
    reset request and we can't check that the reset
    gets de-asserted by the node
    """
    with dl.DeltaGraph() as graph:
        shaper = HwResetShaper(name='reset_shaper')
        shaper_runner = shaper.call(pulse_in=1)
        checker = LengthChecker(5)
        checker.check_shape(shaper_runner.reset_out)

    return graph, shaper


def generate_graph_interactive_input():
    """This function returns instead a cyclic graph:

     -> Checker -> one_shot_run -> HwResetShaper-
    |                                            |
     --------------------------------------------
    In this way we can assert and de-assert the reset
    and verify that the migen code extend the reset
    signal for N clock cycles
    """
    with dl.DeltaGraph() as graph:
        ph = dl.placeholder_node_factory()
        oneshot = one_shot_run.call(status=ph)
        shaper = HwResetShaper(name='reset_shaper_one_shot',
                               vcd_name='reset_shaper_one_shot.vcd')
        shaper_runner = shaper.call(pulse_in=oneshot)
        checker = LengthChecker(5, interactive=True).check_shape(
            shaper_runner.reset_out)
        ph.specify_by_node(checker)

    return graph, shaper


def main(simple):
    if simple:
        graph, _ = generate_graph_constant_input()
    else:
        graph, _ = generate_graph_interactive_input()

    rt = dl.DeltaPySimulator(graph, lvl=logging.ERROR)
    rt.run()


if __name__ == "__main__":
    main(False)
    main(True)
