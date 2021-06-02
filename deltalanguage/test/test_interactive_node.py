import unittest

import deltalanguage as dl

from deltalanguage.test._node_lib import add_interactive_once


class InteractiveNodeGeneralTest(unittest.TestCase):
    """Test how interactive nodes can be defined and initialized in the graph
    context.
    """

    def test_interactive_node_without_io(self):
        """Interactive node must have I/O.

        We chose this rule because runtime simulators,
        in particular the Python GIL, wouldn't know when to
        interrupt this node simulation.

        In order to allow such nodes we need to change the simulation strategy.
        """

        with self.assertRaises(dl.data_types.DeltaIOError):
            @dl.Interactive()
            def _bar(node):
                while True:
                    pass

    def test_interactive_node_without_ports(self):
        """An interactive node with I/O can be just forgotten during graph
        construction. We check that it is connected.
        """
        @dl.Interactive(outputs=[('output', int)])
        def bar(node):
            node.send(1)

        with dl.DeltaGraph() as graph:
            bar.call()

        with self.assertRaises(dl.data_types.DeltaIOError):
            graph.check()

    def test_interactive_inputs_by_position(self):
        """Test that interactive inputs can now be given positionally in
        wiring.
        """
        with dl.DeltaGraph() as graph:
            add_interactive_once.call(1, 2)

        self.assertTrue(graph.check())

    def test_interactive_inputs_by_hybrid(self):
        """Test that interactive inputs can now be given positionally and
        by keyword at the same time in wiring.
        """
        with dl.DeltaGraph() as graph:
            add_interactive_once.call(90, n2=7.7)

        self.assertTrue(graph.check())


if __name__ == "__main__":
    unittest.main()
