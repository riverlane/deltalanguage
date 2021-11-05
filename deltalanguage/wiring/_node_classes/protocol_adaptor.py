import math

import migen
from migen.genlib.fifo import SyncFIFO


class ProtocolAdaptor(migen.Module):
    """Provides an interface to an FPGA node. Handles a Synchronous FIFO for
    the PA data storage

    Parameters
    ----------
    buf_width : int, optional
        Width of the FIFO buffer, by default 8
    buf_depth : int, optional
        Depth of the FIFO buffer, by default 16
    buf_afull : int, optional
        Parameter to specify a threshold of FIFO buffer capacity, i.e. if
        this threshold is met we should not accept any incoming data,
        therefore enforce a backpressure, by default 5

    Attributes
    ----------
    Prefixes:
        wr_: signals corresponding to writing to the PA
        rd_: signals corresponding to reading from the PA
    Suffixes:
        _in: signals going into PA from producers/consumers
        _out: signals coming from the PA to producers/consumers

    wr_data_in: migen.Signal
        The input data
    wr_valid_in: migen.Signal
        Control signal indicating that the incoming data is valid
    wr_ready_out: migen.Signal
        The PA is ready to receive data

    rd_data_out: migen.Signal
        The output data
    rd_valid_out: migen.Signal
        Control signal indicating that the outgoing data is valid
    rd_ready_in: migen.Signal
        The consumer node attached to the PA is ready to receive data

    num_fifo_elements: migen.Signal
        The number of stored elements in the PA

    cnt: migen.Signal
        A count of the stored elements in the PA
    almost_full: migen.Signal
        A flag to signify that the FIFO capacity threshold has been met
    """

    def __init__(self, buf_width=8, buf_depth=16, buf_afull=5):

        # write port
        self.wr_valid_in = migen.Signal(1)
        self.wr_data_in = migen.Signal(buf_width)
        self.wr_ready_out = migen.Signal(1)

        # read port
        self.rd_data_out = migen.Signal(buf_width)
        self.rd_valid_out = migen.Signal(1)
        self.rd_ready_in = migen.Signal(1)

        self.num_fifo_elements = migen.Signal(math.ceil(math.log2(buf_depth)) + 1)

        # Create port map
        wr_itf = {self.wr_valid_in,
                  self.wr_data_in,
                  self.wr_ready_out,
                  self.num_fifo_elements}
        rd_iff = {self.rd_data_out, self.rd_valid_out, self.rd_ready_in}
        self.ios = set(wr_itf) | set(rd_iff)

        # internals
        self.cnt = migen.Signal(math.ceil(math.log2(buf_depth)) + 1)
        self.almost_full = migen.Signal(1)

        ####

        # fifo submodule
        self.submodules.fifo = fifo = SyncFIFO(buf_width, buf_depth)

        self.comb += [
            migen.If(  # write logic
                fifo.writable & self.wr_valid_in & ~self.almost_full,
                fifo.we.eq(1),
                fifo.din.eq(self.wr_data_in)
            ),
            migen.If(  # read logic
                fifo.readable & self.rd_ready_in,
                fifo.re.eq(1),
                self.rd_data_out.eq(fifo.dout)
            ),
            migen.If(  # assert rd valid if fifo is not empty
                fifo.readable,
                self.rd_valid_out.eq(1)
            )
        ]

        # element counter
        self.sync += [
            migen.If(
                fifo.we & (~fifo.re),
                self.cnt.eq(self.cnt + 1)
            ).Elif(
                fifo.re & (~fifo.we),
                self.cnt.eq(self.cnt - 1)
            ).Else(
                self.cnt.eq(self.cnt)
            )
        ]

        # almost full
        self.comb += [
            migen.If(
                (self.cnt >= buf_depth - buf_afull),
                self.almost_full.eq(1)
            ).Else(
                self.almost_full.eq(0)
            ),

            self.wr_ready_out.eq(~self.almost_full),  # back-pressure
            self.num_fifo_elements.eq(self.cnt)  # usedw
        ]
