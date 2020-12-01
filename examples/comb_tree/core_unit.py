from migen import Module, If, Signal

from commands import Commands


class CoreUnit(Module):
    def __init__(self, a_in, b_in, y_out, cmd, err, NBITS):
        # generics
        self.NBITS = NBITS

        # inputs
        self.a_in = a_in
        self.b_in = b_in
        self.y_out = y_out
        self.cmd = cmd
        self.err = err
        
        #internals
        self.sum = Signal(NBITS+1)
        ###

        self.comb += [
            If(
                self.cmd == Commands.MIN,
                self.err.eq(0),
                If(
                    self.a_in < self.b_in,
                    self.y_out.eq(self.a_in)
                ).Else(
                    self.y_out.eq(self.b_in)
                )
            ).Elif(
                self.cmd == Commands.MAX,
                self.err.eq(0),
                If(
                    self.a_in > self.b_in,
                    self.y_out.eq(self.a_in)
                ).Else(
                    self.y_out.eq(self.b_in)
                )
            ).Elif(
                self.cmd == Commands.SUM,
                self.err.eq(0),
                self.y_out.eq(self.a_in + self.b_in)
            ).Elif(
                self.cmd == Commands.AVG,
                self.err.eq(0),
                self.sum.eq(self.a_in + self.b_in),
                If(
                    self.sum != 0,
                    self.y_out.eq(self.sum >> 1)
                ).Else(
                    self.y_out.eq(self.sum)
                )
            ).Else(
                self.err.eq(1)
            )
        ]
