import random
from types import SimpleNamespace
import unittest

from migen import run_simulation

import deltalanguage as dl
from deltalanguage.runtime import DeltaQueue
from deltalanguage.wiring import InPort, OutPort, ProtocolAdaptor
from deltalanguage._utils import QueueMessage


class MigenProtocalAdapterTest(unittest.TestCase):

    def setUp(self) -> None:
        self.tb_buf_width = 8
        self.tb_buf_depth = 16
        self.tb_buf_afull = 5

    def test_write_read(self):
        """Test to show data can be written to and read from the PA FIFO in a
        serial manner.
        """

        def tb_write_read(pa):
            # FIFO is empty
            yield
            self.assertEqual((yield pa.rd_valid_out), 0)
            self.assertEqual((yield pa.wr_ready_out), 1)
            self.assertEqual((yield pa.rd_data_out), 0)

            # set ready_i to 1 [trying to read but FIFO is EMPTY]
            yield pa.rd_ready_in.eq(1)
            yield
            self.assertEqual((yield pa.rd_valid_out), 0)
            self.assertEqual((yield pa.wr_ready_out), 1)
            self.assertEqual((yield pa.rd_data_out), 0)

            for i in range(20):
                # generate random data
                data = random.randint(0, pow(2, self.tb_buf_width))

                # write to the FIFO
                yield pa.wr_valid_in.eq(1)
                yield pa.wr_data_in.eq(data)
                yield
                self.assertEqual((yield pa.rd_valid_out), 0)
                self.assertEqual((yield pa.wr_ready_out), 1)
                self.assertEqual((yield pa.rd_data_out), 0)

                # read from the FIFO
                yield pa.wr_valid_in.eq(0)
                yield pa.wr_data_in.eq(0)
                yield pa.rd_ready_in.eq(1)
                yield
                self.assertEqual((yield pa.rd_valid_out), 1)
                self.assertEqual((yield pa.wr_ready_out), 1)
                self.assertEqual((yield pa.rd_data_out), data)
                yield

        pa = ProtocolAdaptor(
            self.tb_buf_width, self.tb_buf_depth, self.tb_buf_afull
        )
        run_simulation(pa, tb_write_read(pa))

    def test_almost_full(self):
        """Test to show that if the "almost full" parameter is set then at some
        point data cannot be written to the FIFO even though it has enough
        depth.
        The "almost full" parameter defines a threshold where backpressure kicks
        in.
        """

        def tb_almost_full(pa):
            yield
            self.assertEqual((yield pa.rd_valid_out), 0)
            self.assertEqual((yield pa.wr_ready_out), 1)
            self.assertEqual((yield pa.rd_data_out), 0)

            for i in range(self.tb_buf_depth - self.tb_buf_afull):
                # generate random data
                data = random.randint(0, pow(2, self.tb_buf_width))

                # write to the FIFO
                yield pa.wr_valid_in.eq(1)
                yield pa.wr_data_in.eq(data)
                yield
                if i == 0:
                    self.assertEqual((yield pa.rd_valid_out), 0)
                else:
                    self.assertEqual((yield pa.rd_valid_out), 1)
                self.assertEqual((yield pa.wr_ready_out), 1)
                self.assertEqual((yield pa.rd_data_out), 0)

            # FIFO is almost full
            yield
            self.assertEqual((yield pa.rd_valid_out), 1)
            self.assertEqual((yield pa.wr_ready_out), 0)
            self.assertEqual((yield pa.rd_data_out), 0)

            # try to write to almost full FIFO
            yield pa.wr_valid_in.eq(1)
            yield pa.wr_data_in.eq(255)
            yield
            self.assertEqual((yield pa.rd_valid_out), 1)
            self.assertEqual((yield pa.wr_ready_out), 0)
            self.assertEqual((yield pa.rd_data_out), 0)

        pa = ProtocolAdaptor(
            self.tb_buf_width, self.tb_buf_depth, self.tb_buf_afull
        )
        run_simulation(pa, tb_almost_full(pa))

    def test_write_to_full_pa_fifo(self):
        """Test that data cannot be written to the PA FIFO if it is full. This
        also tests that we can read from the FIFO, and when we do, this frees up
        space for additional data to be written to it.
        """

        def tb_write_to_full_pa_fifo(pa):

            yield
            self.assertEqual((yield pa.rd_valid_out), 0)
            self.assertEqual((yield pa.wr_ready_out), 1)
            self.assertEqual((yield pa.rd_data_out), 0)

            yield pa.rd_ready_in.eq(0)
            # fill up the FIFO so its full
            data = []
            for i in range(self.tb_buf_depth):
                # generate random entry
                d = random.randint(0, pow(2, self.tb_buf_width))
                data.append(d)  # add entry to reference data for checking

                # write to the FIFO
                yield
                yield pa.wr_valid_in.eq(1)
                yield pa.wr_data_in.eq(d)
                yield
                yield pa.wr_valid_in.eq(0)
                yield

            # check FIFO is full
            self.assertEqual((yield pa.fifo.dout), data[0])
            self.assertEqual((yield pa.fifo.we), 0)
            self.assertEqual((yield pa.almost_full), 1)
            self.assertEqual((yield pa.num_fifo_elements), self.tb_buf_depth)

            # try writing more
            for i in range(5):
                # generate random entry
                d = random.randint(0, pow(2, self.tb_buf_width))

                # write to the FIFO
                yield
                yield pa.wr_valid_in.eq(1)
                yield pa.wr_data_in.eq(d)
                yield
                yield pa.wr_valid_in.eq(0)
                yield

            # check count hasn't changed
            self.assertEqual((yield pa.fifo.dout), data[0])
            self.assertEqual((yield pa.fifo.we), 0)
            self.assertEqual((yield pa.almost_full), 1)
            self.assertEqual((yield pa.num_fifo_elements), self.tb_buf_depth)

            # read a single entry from the FIFO (the first entry)
            yield pa.rd_ready_in.eq(1)
            yield
            self.assertEqual((yield pa.rd_valid_out), 1)
            self.assertEqual((yield pa.rd_data_out), data[0])
            yield pa.rd_ready_in.eq(0)
            yield
            data.pop(0)  # remove first entry from reference data

            # write a single element to the FIFO
            # generate random entry
            d = random.randint(0, pow(2, self.tb_buf_width))
            data.append(d)  # add new entry to end of reference data

            # write to the FIFO
            yield
            yield pa.wr_valid_in.eq(1)
            yield pa.wr_data_in.eq(d)
            yield
            yield pa.wr_valid_in.eq(0)
            yield

            # check count hasn't changed
            self.assertEqual((yield pa.almost_full), 1)
            self.assertEqual((yield pa.num_fifo_elements), self.tb_buf_depth)

            # check original first entry in FIFO is gone and all others remain
            for d in data:
                yield pa.rd_ready_in.eq(1)
                yield
                self.assertEqual((yield pa.rd_data_out), d)
                yield pa.rd_ready_in.eq(0)
                yield

        pa = ProtocolAdaptor(self.tb_buf_width, self.tb_buf_depth, 0)
        run_simulation(pa, tb_write_to_full_pa_fifo(pa))

    def test_deltaqueue_to_pa(self):
        """Test that emulates a DeltaQueue interacting with the PA. Data is
        moved from the DeltaQueue into the FIFO only when the FIFO is not full.
        """

        def tb_deltaqueue_to_pa(pa):

            def transfer_queue_to_pa(queue, pa):
                """Emulates the movement of data from the DeltaQueue to a PA
                """
                if (yield pa.almost_full) != 1:

                    # write to the PA FIFO
                    yield
                    yield pa.wr_valid_in.eq(1)
                    yield pa.wr_data_in.eq(queue.get().msg)
                    yield
                    yield pa.wr_valid_in.eq(0)
                    yield

            # First create a DeltaQueue object
            # Hack: OutPort needs a "node" object with full_name attribute
            mock_parent_node = SimpleNamespace()
            mock_parent_node.full_name = "parent_node"

            in_port = InPort("in", dl.Int(), None, self.tb_buf_width)
            in_queue = DeltaQueue(
                OutPort("out", dl.Int(), in_port, mock_parent_node),
                maxsize=self.tb_buf_depth + 1
            )

            # fill up the DeltaQueue so it has more items than the PA FIFO
            data = []
            for i in range(self.tb_buf_depth + 1):
                # generate random entry
                d = random.randint(0, pow(2, self.tb_buf_width))
                data.append(d)  # add entry to reference data for checking
                in_queue.put(QueueMessage(d))

            # check size of DeltaQueue
            self.assertEqual(in_queue.qsize(), self.tb_buf_depth + 1)

            # ensure PA is ready for consuming
            yield
            self.assertEqual((yield pa.rd_valid_out), 0)
            self.assertEqual((yield pa.wr_ready_out), 1)
            self.assertEqual((yield pa.rd_data_out), 0)

            yield pa.rd_ready_in.eq(0)

            # fill up the PA FIFO from the DeltaQueue until its full
            for i in range(in_queue.qsize()):
                yield from transfer_queue_to_pa(in_queue, pa)

            # check PA FIFO is full
            self.assertEqual((yield pa.fifo.dout), data[0])
            self.assertEqual((yield pa.fifo.we), 0)
            self.assertEqual((yield pa.almost_full), 1)
            self.assertEqual((yield pa.num_fifo_elements), self.tb_buf_depth)
            # check size of DeltaQueue
            self.assertEqual(in_queue.qsize(), 1)

            # read a single entry from the PA FIFO (the first entry)
            yield pa.rd_ready_in.eq(1)
            yield
            self.assertEqual((yield pa.rd_valid_out), 1)
            self.assertEqual((yield pa.rd_data_out), data[0])
            yield pa.rd_ready_in.eq(0)
            yield
            data.pop(0)  # remove first entry from reference data

            # try and add remaining DeltaQueue data to the PA FIFO
            for i in range(in_queue.qsize()):

                if (yield pa.almost_full) != 1:
                    yield from transfer_queue_to_pa(in_queue, pa)

            # check PA FIFO count hasn't changed
            self.assertEqual((yield pa.almost_full), 1)
            self.assertEqual((yield pa.num_fifo_elements), self.tb_buf_depth)
            # check size of DeltaQueue
            self.assertEqual(in_queue.qsize(), 0)

            # check original first entry in PA FIFO is gone and all others remain
            for d in data:
                yield pa.rd_ready_in.eq(1)
                yield
                self.assertEqual((yield pa.rd_data_out), d)
                yield pa.rd_ready_in.eq(0)
                yield

        pa = ProtocolAdaptor(self.tb_buf_width, self.tb_buf_depth, 0)
        run_simulation(pa, tb_deltaqueue_to_pa(pa))

    def test_pa_to_deltaqueue(self):
        """Test that emulates the PA interacting with a DeltaQueue. Data is
        moved from the PA FIFO into the DeltaQueue only if the DeltaQueue is
        not full.
        """

        def tb_pa_to_deltaqueue(pa):

            def transfer_pa_to_queue(pa, queue):
                """Emulates the movement of data from the PA to a DeltaQueue
                """
                if not queue.full():

                    # read a single entry from the PA FIFO (the first entry)
                    yield pa.rd_ready_in.eq(1)
                    yield
                    self.assertEqual((yield pa.rd_valid_out), 1)
                    # write to the queue
                    queue.put(QueueMessage((yield pa.rd_data_out)))
                    yield pa.rd_ready_in.eq(0)
                    yield

            # First create a DeltaQueue object
            # Hack: OutPort needs a "node" object with full_name attribute
            mock_parent_node = SimpleNamespace()
            mock_parent_node.full_name = "parent_node"

            in_port = InPort("in", dl.Int(), None, self.tb_buf_width)
            out_queue = DeltaQueue(
                OutPort("out", dl.Int(), in_port, mock_parent_node),
                maxsize=self.tb_buf_depth - 1
            )

            yield
            self.assertEqual((yield pa.rd_valid_out), 0)
            self.assertEqual((yield pa.wr_ready_out), 1)
            self.assertEqual((yield pa.rd_data_out), 0)

            yield pa.rd_ready_in.eq(0)
            # fill up PA FIFO so it has more items than max size of the DeltaQueue
            data = []
            for i in range(self.tb_buf_depth):
                # generate random entry
                d = random.randint(0, pow(2, self.tb_buf_width))
                data.append(d)  # add entry to reference data for checking

                # write to the PA FIFO
                yield
                yield pa.wr_valid_in.eq(1)
                yield pa.wr_data_in.eq(d)
                yield
                yield pa.wr_valid_in.eq(0)
                yield

            # check PA FIFO is full
            self.assertEqual((yield pa.fifo.dout), data[0])
            self.assertEqual((yield pa.fifo.we), 0)
            self.assertEqual((yield pa.almost_full), 1)
            self.assertEqual((yield pa.num_fifo_elements), self.tb_buf_depth)

            # fill up the DeltaQueue from the PA FIFO until its full
            for i in range(self.tb_buf_depth):
                yield from transfer_pa_to_queue(pa, out_queue)

            # check PA FIFO has been emptied except for 1
            self.assertEqual((yield pa.almost_full), 0)
            self.assertEqual((yield pa.num_fifo_elements), 1)
            # check size of DeltaQueue
            self.assertEqual(out_queue.qsize(), self.tb_buf_depth - 1)

            # get a single item from the DeltaQueue
            self.assertEqual(out_queue.get().msg, data[0])
            data.pop(0)  # remove first entry from reference data

            # try and add remaining PA FIFO data to the DeltaQueue
            for i in range((yield pa.num_fifo_elements)):
                yield from transfer_pa_to_queue(pa, out_queue)

            # check PA FIFO has been emptied
            self.assertEqual((yield pa.almost_full), 0)
            self.assertEqual((yield pa.num_fifo_elements), 0)
            # check size of DeltaQueue
            self.assertEqual(out_queue.qsize(), self.tb_buf_depth - 1)

            # check the remaining data was moved into the DeltaQueue
            for i in range(out_queue.qsize()):
                self.assertEqual(out_queue.get().msg, data[i])

        pa = ProtocolAdaptor(self.tb_buf_width, self.tb_buf_depth, 0)
        run_simulation(pa, tb_pa_to_deltaqueue(pa))


if __name__ == "__main__":
    unittest.main()
