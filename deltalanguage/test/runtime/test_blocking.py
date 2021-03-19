import time
import unittest

import deltalanguage as dl


TIME_DIFF = 0
SLEEPTIME = 1e-3
STORE = []


@dl.Interactive([], int, name="send_and_check_time")
def send_and_check_time(node: dl.PythonNode):
    """This node should be blocked at ``send`` if the receiving node is busy
    and the queue is full.
    """
    t1 = time.time()

    # this one will go through to the destination node and keep it busy
    node.send(1)

    # this one will be sitting on the queue
    node.send(2)

    # if the queue size is 1 this one will block this node
    node.send(3)

    t2 = time.time()

    global TIME_DIFF
    TIME_DIFF = t2-t1

    raise dl.DeltaRuntimeExit


class BlockingQueueTest(unittest.TestCase):
    """Test that a full queue will block the sending node.

    The size of the queue is defined by the simulator in one of 2 ways
    shown in tests below.

    The lower time bound is quite clear and should not be breached.

    The upper time bound is quite high, if it's breached something
    dodgy is going on.

    Note the key None is used if a node has only 1 out_queue.
    """

    def setUp(self):
        global TIME_DIFF
        TIME_DIFF = 0

    def test_blocking_queue_in_port_size(self):
        """The queue size is defined locally by in_port_size."""
        @dl.DeltaBlock(allow_const=False, in_port_size=1)
        def receive_then_sleep(n: int) -> dl.Void:
            time.sleep(SLEEPTIME)

        for _ in range(100):
            with dl.DeltaGraph() as graph:
                n = send_and_check_time.call()
                receive_then_sleep(n)

            dl.DeltaPySimulator(graph).run(100*SLEEPTIME)

            self.assertGreaterEqual(TIME_DIFF, SLEEPTIME)

        self.assertEqual(n.out_queues[None].maxsize, 1)

    def test_blocking_queue_queue_size(self):
        """The queue size is defined globally by queue_size."""
        @dl.DeltaBlock(allow_const=False)
        def receive_then_sleep(n: int) -> dl.Void:
            time.sleep(SLEEPTIME)

        for _ in range(100):
            with dl.DeltaGraph() as graph:
                n = send_and_check_time.call()
                receive_then_sleep(n)

            dl.DeltaPySimulator(graph, queue_size=1).run(100*SLEEPTIME)

            self.assertGreaterEqual(TIME_DIFF, SLEEPTIME)

        self.assertEqual(n.out_queues[None].maxsize, 1)

    def test_queue_size(self):
        """If both queue_size and in_port_size are defined, the minimum is
        chosen."""
        @dl.DeltaBlock(allow_const=False, in_port_size=2)
        def receive_then_sleep(n: int) -> dl.Void:
            time.sleep(SLEEPTIME)

        with dl.DeltaGraph() as graph:
            n = send_and_check_time.call()
            receive_then_sleep(n)

        # 1 < 2
        dl.DeltaPySimulator(graph, queue_size=1)
        self.assertEqual(n.out_queues[None].maxsize, 1)

        # 2 < 3
        dl.DeltaPySimulator(graph, queue_size=3)
        self.assertEqual(n.out_queues[None].maxsize, 2)


class RuntimeBlockingTest(unittest.TestCase):
    """Test situations when the executuion of the graph can get stuck
    due to various reasons.

    Below we consider this issue on the case-by-case basis.

    To measure speed we use 1 sec time limit, which is quite arbitrary and
    chosen with a large safety bugger.
    The number of iterations is chosen such that 1 sec sits somewhere in
    the middle between the current simulation (~10x faster) time and how
    long it takes when the simulation is called inefficient (~10x slower).
    """

    def setUp(self):
        global STORE
        STORE = []

    def test_portless_node(self):
        """This test has a node without inputs nor outputs.

        We test that DeltaPySimulator does not get stuck on running just this
        node and instead runs every node (the order is not determined).

        This is implemented via addition of a 1 ns wait when a node attempts
        to send an output.
        """
        N_ITER = 1000

        @dl.DeltaBlock(allow_const=False)
        def foo() -> dl.Void:
            a = 40
            b = 2
            a, b = b, a

        gen = dl.lib.make_generator(1, reps=N_ITER)
        s = dl.lib.StateSaver(int)

        @dl.Interactive([('a', int)], int)
        def aggregator(node):
            result = 0
            for _ in range(N_ITER):
                a = node.receive('a')
                result += a

            node.send(result)

        with dl.DeltaGraph() as graph:
            foo()
            s.save_and_exit(aggregator.call(a=gen.call()))

        start_time = time.time()
        dl.DeltaPySimulator(graph).run()
        total_time = time.time() - start_time

        self.assertEqual(s.saved, [N_ITER])
        self.assertLessEqual(total_time, 1)

    def test_interactive_node_with_only_optional_input(self):
        """Test that an interactive node with an only optional input and no
        outputs or outputs that can be reached only in a special case wouldn't
        block the simulation.

        This is implemented via addition of a 1 ns wait when a node attempts
        to receive an input and it's trivial.

        Note that non-interactive nodes with such behaviour won't block as
        they always call ``send``.
        """

        @dl.Interactive([('a', dl.DOptional(int))], dl.Void)
        def node_to_investigate(node):
            while True:
                a = node.receive('a')
                if a is not None:
                    STORE.append(a)
                    raise dl.DeltaRuntimeExit

        @dl.Interactive([], int)
        def rest_of_graph(node):
            """This node imitates the rest of the graph that does some
            computations and occasionally provides an input."""
            i = 0
            while True:
                i += 1
                a = 40
                b = 2
                a, b = b, a
                if i % 1000 == 0:
                    node.send(10)
                else:
                    node.send(None)

        with dl.DeltaGraph() as graph:
            opt_input = rest_of_graph.call()
            node_to_investigate.call(a=opt_input)

        start_time = time.time()
        dl.DeltaPySimulator(graph).run()
        total_time = time.time() - start_time

        self.assertEqual(STORE, [10])
        self.assertLessEqual(total_time, 1)

    def test_interactive_node_without_input(self):
        """Similar to the test above, but here the tests node does not have
        inputs.
        """
        @dl.Interactive(inputs=[], outputs=int)
        def unstoppable(node):
            i = 0
            while True:
                node.send(i)
                i = i + 1

        exit_if = dl.lib.StateSaver(int, condition=lambda x: x > 10)
        with dl.DeltaGraph() as graph:
            exit_if.save_and_exit_if(unstoppable.call())

        rt = dl.DeltaPySimulator(graph)
        rt.run()

        unstoppable = graph.find_node_by_name("unstoppable")

        self.assertFalse(rt.threads[unstoppable.name].is_alive())
        self.assertEqual(exit_if.saved, list(range(12)))


if __name__ == "__main__":
    unittest.main()
