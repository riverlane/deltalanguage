import unittest
import deltalanguage as dl
from deltalanguage.test._graph_lib import (getg_const_chain,
                                           getg_optional_queues,
                                           getg_PyFunc_body_graph,
                                           getg_PyInteractiveBody_one_in_one_out,
                                           getg_PyInteractiveBody_one_in_two_out,
                                           getg_PyInteractiveBody_two_in_one_out,
                                           getg_PyInteractiveBody_two_in_two_out,
                                           getg_optional_const,
                                           getg_splitting_const_const_same,
                                           getg_splitting_const_const_same_and_diff)


class GraphDeserialisationTest(unittest.TestCase):

    def check_serialise_deserialise_isomorphism(self, graph):
        """Ensure that a given graph can be serialised and then deserialised,
        and that the graph is unchanged accoridng to the definion of graph
        equality.

        In all the bodies of the graph under test, there can be no reference
        to the DeltaLanguage package.
        This is only not possible because we are currently inside the package
        itself.

        Parameters
        ----------
        graph : DeltaGraph
            Graph under test
        """
        _, program = dl.serialize_graph(graph)
        de_graph = dl.DeltaGraph.from_capnp(program)
        self.assertEqual(graph, de_graph)

    def test_deserialize_graph_node_library(self):
        """Ensure that a selection of the graphs from the graph library
        meet the deserialisation check.
        """
        graphs_to_check = [
            getg_const_chain(),
            getg_optional_queues(),
            getg_PyFunc_body_graph(),
            getg_PyInteractiveBody_one_in_one_out(),
            getg_PyInteractiveBody_one_in_two_out(),
            getg_PyInteractiveBody_two_in_one_out(),
            getg_PyInteractiveBody_two_in_two_out(),
            getg_optional_const(),
            getg_splitting_const_const_same(),
            getg_splitting_const_const_same_and_diff()
        ]

        for g in graphs_to_check:
            self.check_serialise_deserialise_isomorphism(g)


if __name__ == "__main__":
    unittest.main()
