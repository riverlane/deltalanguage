"""Testing for naming errors for out-ports
"""

import unittest
from typing import Tuple

from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  DeltaMethodBlock,
                                  Interactive,
                                  NodeTemplate,
                                  placeholder_node_factory)


@DeltaBlock(outputs=[('send', int), ('y', int)])
def forked_block() -> Tuple[int, int]:
    return 1, 2


class OutportClashNameMethodClass:

    @DeltaMethodBlock(outputs=[('send', int), ('y', int)])
    def forked_method_block(self) -> Tuple[int, int]:
        return 1, 2


@Interactive(outputs=[('send', int), ('y', int)])
def interactive_forked(node):
    node.send(3, 4)


class NamingForkTest(unittest.TestCase):
    """Test that a node with some outports will raise an error if
    one of those outport names clashes with existing node attributes
    """

    def test_func_outport_name_clash(self):
        with self.assertRaises(NameError):
            with DeltaGraph():
                forked_block()

    def test_placeholder_outport_name_clash(self):
        with self.assertRaises(NameError):
            with DeltaGraph():
                p = placeholder_node_factory()
                p.specify_by_func(forked_block)

    def test_method_outport_name_clash(self):
        with self.assertRaises(NameError):
            instance = OutportClashNameMethodClass()
            with DeltaGraph():
                instance.forked_method_block()

    def test_interactive_outport_name_clash(self):
        with self.assertRaises(NameError):
            with DeltaGraph():
                interactive_forked.call()

    def test_template_outport_name_clash(self):
        forked_template = NodeTemplate(outputs=[('send', int), ('y', int)])

        with self.assertRaises(NameError):
            with DeltaGraph():
                forked_template.call()


if __name__ == "__main__":
    unittest.main()
