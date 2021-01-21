"""Testing for fork naming errors
"""

import unittest

from deltalanguage.data_types import make_forked_return
from deltalanguage.wiring import (DeltaGraph,
                                  placeholder_node_factory,
                                  DeltaBlock,
                                  DeltaMethodBlock,
                                  Interactive)

ForkT, Fork = make_forked_return(
    {
        'send': int,
        'y': int
    }
)


@DeltaBlock()
def forked_block() -> ForkT:
    return Fork(1, 2)


class ForkNameTestClass:

    @DeltaMethodBlock()
    def forked_method_block(self) -> ForkT:
        return Fork(1, 2)


@Interactive(in_params={}, out_type=ForkT, name="ForkedInteractive")
def interactive_forked(node):
    node.send(Fork(3, 4))


class NamingForkTest(unittest.TestCase):

    def test_forked_block_naming(self):
        """Test that checks a forked DeltaBlock raises an error if the fork
           names clash with node attributes
        """

        with self.assertRaises(NameError):
            with DeltaGraph():
                forked_block()

    def test_forked_placeholder_naming(self):
        """Test that checks a forked placeholder raises an error if the fork
           names clash with node attributes
        """
        with self.assertRaises(NameError):
            with DeltaGraph():
                p = placeholder_node_factory()
                p.specify_by_func(forked_block)

    def test_forked_method_block_naming(self):
        """Test that checks a forked DeltaMethodBLock raises an error if the 
           fork names clash with node attributes
        """
        with self.assertRaises(NameError):
            instance = ForkNameTestClass()
            with DeltaGraph():
                instance.forked_method_block()

    def test_forked_interactive_naming(self):
        """Test that checks a forked Interactive raises an error if the fork
           names clash with node attributes
        """
        with self.assertRaises(NameError):
            with DeltaGraph():
                interactive_forked.call()


if __name__ == "__main__":
    unittest.main()
