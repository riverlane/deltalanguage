"""Collection of nodes used in tests.

If any of the components become useful for examples and more general use
please move it to `deltalanguage.lib`.
"""

import time

import migen

import deltalanguage as dl
from deltalanguage import DeltaRuntimeExit

# Add: 2 inputs, 1 output


@dl.DeltaBlock(allow_const=True)
def add_const(n1: int, n2: int) -> int:
    return n1 + n2


@dl.DeltaBlock(allow_const=False)
def add_non_const(n1: int, n2: int) -> int:
    return n1 + n2


@dl.DeltaBlock(allow_const=False)
def add_optional(n1: dl.Optional(int), n2: int) -> int:
    if n1:
        return n1 + n2
    else:
        return n2


@dl.Interactive([('n1', int), ('n2', int)], [('output', int)])
def add_interactive_once(node):
    n1 = node.receive('n1')
    n2 = node.receive('n2')
    node.send(n1 + n2)


@dl.Interactive([('n1', int), ('n2', int)], [('output', int)])
def add_interactive_twice(node):
    for _ in range(2):
        n1 = node.receive('n1')
        n2 = node.receive('n2')
        node.send(n1 + n2)


@dl.Interactive([('n1', int), ('n2', int)], [('output', int)])
def add_interactive_loop(node):
    while True:
        n1 = node.receive('n1')
        n2 = node.receive('n2')
        node.send(n1 + n2)


@dl.Interactive([('n1', int), ('n2', int)], [('output', int)])
def add_interactive_loop_staggerd(node):
    while True:
        n1 = node.receive('n1')
        n2 = node.receive('n2')
        n1 += node.receive('n1')
        n2 += node.receive('n2')
        node.send(n1 + n2)


@dl.Interactive([('n1', dl.Optional(int)), ('n2', int)], [('output', int)])
def add_interactive_loop_optional(node):
    while True:
        n1 = node.receive('n1')
        n2 = node.receive('n2')
        if n1:
            node.send(n1 + n2)
        else:
            node.send(n2)


# Increment: 1 input, 1 output


@dl.DeltaBlock(allow_const=True)
def increment_const(val: int) -> int:
    return val + 1


@dl.DeltaBlock(allow_const=False)
def increment_non_const(val: int) -> int:
    return val + 1


@dl.Interactive([('val', int)], [('output', int)])
def increment_interactive_once(node):
    node.send(node.receive('val') + 1)


@dl.Interactive([('val', int)], [('output', int)])
def increment_interactive_twice(node):
    for _ in range(2):
        node.send(node.receive('val') + 1)


@dl.Interactive([('val', int)], [('output', int)])
def increment_interactive_loop(node):
    while True:
        node.send(node.receive('val') + 1)


# Forward: 1 input, 1 output


@dl.DeltaBlock(allow_const=True)
def forward_const(val: int) -> int:
    return val


@dl.DeltaBlock(allow_const=False)
def forward_non_const(val: int) -> int:
    return val


@dl.Interactive([('val', int)], [('output', int)])
def forward_interactive_once(node):
    node.send(node.receive('val'))


@dl.Interactive([('val', int)], [('output', int)])
def forward_interactive_twice(node):
    for _ in range(2):
        node.send(node.receive('val'))


@dl.Interactive([('val', int)], [('output', int)])
def forward_interactive_loop(node):
    while True:
        node.send(node.receive('val'))


# Return: 0 input, 1 output


@dl.DeltaBlock(allow_const=True)
def return_1_const() -> int:
    return 1


@dl.DeltaBlock(allow_const=False)
def return_1_non_const() -> int:
    return 1


@dl.Interactive([], [('output', int)])
def return_1_interactive_once(node):
    node.send(1)


@dl.Interactive([], [('output', int)])
def return_1_interactive_twice(node):
    for _ in range(2):
        node.send(1)


@dl.Interactive([], [('output', int)])
def return_1_interactive_loop(node):
    while True:
        node.send(1)


@dl.DeltaBlock(allow_const=True)
def return_2_const() -> int:
    return 2


@dl.DeltaBlock(allow_const=False)
def return_2_non_const() -> int:
    return 2


@dl.DeltaBlock(allow_const=False)
def return_nothing() -> int:
    time.sleep(0.1)
    return None


# Return: 0 input, 2 outputs


@dl.DeltaBlock(outputs=[('x', int), ('y', int)], allow_const=True)
def return_1_2_const():
    return 1, 2


@dl.DeltaBlock(outputs=[('x', int), ('y', int)], allow_const=False)
def return_1_2_non_const():
    return 1, 2


@dl.Interactive([], [('x', int), ('y', int)])
def return_1_2_interactive_once(node):
    node.send(1, 2)


@dl.Interactive([], [('x', int), ('y', int)])
def return_1_2_interactive_twice(node):
    for _ in range(2):
        node.send(1, 2)


@dl.Interactive([], [('x', int), ('y', int)])
def return_1_2_interactive_loop(node):
    while True:
        node.send(1, 2)


# Terminate: 1 input, 0 output


@dl.DeltaBlock(allow_const=False)
def terminate_const(val: int) -> dl.Void:
    pass


@dl.DeltaBlock(allow_const=False)
def terminate_non_const(val: int) -> dl.Void:
    pass


# Mix: 2 inputs, 2 outputs


@dl.DeltaBlock(outputs=[('x', int), ('y', int)], allow_const=True)
def mix_const(n1: int, n2: int):
    return n1 + n2, n1 * n2


@dl.DeltaBlock(outputs=[('x', int), ('y', int)], allow_const=False)
def mix_non_const(n1: int, n2: int) -> int:
    return n1 + n2, n1 * n2


@dl.DeltaBlock(outputs=[('x', int), ('y', int)], allow_const=False)
def mix_optional(n1: dl.Optional(int), n2: int) -> int:
    if n1:
        return n1 + n2, n1 * n2
    else:
        return n2, n2


@dl.Interactive([('n1', int), ('n2', int)], [('x', int), ('y', int)])
def mix_interactive_once(node):
    n1 = node.receive('n1')
    n2 = node.receive('n2')
    node.send(n1 + n2, n1 * n2)


@dl.Interactive([('n1', int), ('n2', int)], [('x', int), ('y', int)])
def mix_interactive_twice(node):
    for _ in range(2):
        n1 = node.receive('n1')
        n2 = node.receive('n2')
        node.send(n1 + n2, n1 * n2)


@dl.Interactive([('n1', int), ('n2', int)], [('x', int), ('y', int)])
def mix_interactive_loop(node):
    while True:
        n1 = node.receive('n1')
        n2 = node.receive('n2')
        node.send(n1 + n2, n1 * n2)


@dl.Interactive([('n1', int), ('n2', int)], [('x', int), ('y', int)])
def mix_interactive_loop_staggered(node):
    while True:
        n1 = node.receive('n1')
        n2 = node.receive('n2')
        n1 += node.receive('n1')
        n2 += node.receive('n2')
        node.send(n1 + n2, n1 * n2)


@dl.Interactive([('n1', dl.Optional(int)), ('n2', int)],
                [('x', int), ('y', int)])
def mix_interactive_loop_optional(node):
    while True:
        n1 = node.receive('n1')
        n2 = node.receive('n2')
        if n1:
            node.send(n1 + n2, n1 * n2)
        else:
            node.send(n2, n2)


# Miscellaneous


class DUT1(dl.MigenNodeTemplate):

    def migen_body(self, template):
        # I/O:
        i1 = template.add_pa_in_port("i1", dl.Optional(int))
        o1 = template.add_pa_out_port("o1", int)

        # LOGIC:
        self.counter = migen.Signal(1000)
        self.sync += self.counter.eq(self.counter + 1)

        # Two memories for testing
        self.specials.mem1 = mem1 = migen.Memory(32, 100, init=[5, 15, 32])
        read_port1 = mem1.get_port()
        self.specials.mem2 = mem2 = migen.Memory(32, 100, init=[2, 4, 6, 8])
        read_port2 = mem2.get_port()
        self.specials += read_port1
        self.specials += read_port2
        self.mem_out1 = migen.Signal(32)
        self.mem_out2 = migen.Signal(32)

        self.sync += (read_port1.adr.eq(self.counter),
                      self.mem_out1.eq(read_port1.dat_r))

        self.sync += (read_port2.adr.eq(self.counter),
                      self.mem_out2.eq(read_port2.dat_r))

        # DEBUGGING:
        # add any signal you want to see in debugging and printing format
        # (in_ports, out_ports, inputs, output are added by default):
        self.debug_signals = {'counter': (self.counter, '05b')}

        self.comb += migen.If(
            self.counter >= 5,
            i1.ready.eq(1)
        )

        self.comb += migen.If(
            o1.ready == 1,
            migen.If(
                self.counter == 10,
                o1.data.eq(self.counter+i1.data),
                o1.valid.eq(1)
            ).Else(
                o1.valid.eq(0)
            )
        )


class MigenIncrementer(dl.MigenNodeTemplate):

    def migen_body(self, template):
        # I/O:
        i1 = template.add_pa_in_port("i1", dl.Optional(int))
        o1 = template.add_pa_out_port("o1", int)

        self.comb += (
            i1.ready.eq(1),
        )

        started = migen.Signal(1)

        self.sync += migen.If(
            i1.valid == 1,
            o1.valid.eq(1),
            o1.data.eq(i1.data+1)
        ).Else(
            o1.data.eq(0),
            migen.If(started == 0,
                     o1.valid.eq(1),
                     started.eq(1)
                     ).Else(
                o1.valid.eq(0)
            )
        )


@dl.Interactive([("measurement", dl.UInt(dl.Size(32)))],
                [("output", dl.UInt(dl.Size(32)))],
                name="interactive_simple")
def send_gates_list_then_exit(node: dl.PythonNode):
    cmds = ["RX", "RZ", "RY"]
    # for non-deterministic tests use random.randint(0, 255)
    args = [99, 250, 11]

    node.send(dl.lib.command_creator("STATE_PREPARATION"))

    for cmd, arg in zip(cmds, args):
        node.send(dl.lib.command_creator(cmd, argument=arg))
    node.send(dl.lib.command_creator("STATE_MEASURE"))

    measurement = node.receive("measurement")
    print(f"Measurement: {measurement}")

    raise DeltaRuntimeExit


class TripleStateSaver:

    def __init__(self, count: int):
        self.max_count = count
        self.curr_count = 0

        self.x_store = []
        self.y_store = []
        self.z_store = []

    @dl.DeltaMethodBlock()
    def multi_count_print_exit(self,
                               x: dl.Optional(int),
                               y: dl.Optional(int),
                               z: dl.Optional(bool)):
        """Count and store messages until we receive self.max_count many, then 
        print all stores and exit.
        """
        if x is not None:
            self.x_store.append(x)
            self.curr_count += 1

        if y is not None:
            self.y_store.append(y)
            self.curr_count += 1

        if z is not None:
            self.z_store.append(z)
            self.curr_count += 1

        if self.curr_count >= self.max_count:
            print(self.x_store)
            print(self.y_store)
            print(self.z_store)
            raise DeltaRuntimeExit


@dl.DeltaBlock(allow_const=False)
def multiplier(a: int) -> int:
    return a*1000


class MigenDUT(dl.MigenNodeTemplate):
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
        in1 = template.add_pa_in_port('in1', dl.Optional(int))
        in2 = template.add_pa_in_port('in2', dl.Optional(int))
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
