import unittest

from deltalanguage.wiring import (DeltaGraph,
                                  PythonBody,
                                  PyFuncBody,
                                  RealNode)


class SelectBody(unittest.TestCase):
    """Tests associated with body selection system
    including how to exclude and prefer different bodies using tags.
    """

    def test_select_body_on_construction(self):
        """Test if single node bodies get their body auto-selected.
        Multi-body nodes do not undergo auto-selection.
        """
        graph = DeltaGraph()
        body_1 = PythonBody()
        test_node = RealNode(graph, [body_1])

        self.assertEqual(test_node.body, body_1)

        body_2 = PythonBody()
        test_node_2 = RealNode(graph, [body_1, body_2])

        with self.assertRaises(ValueError):
            test_node_2.body

    def test_selection_overide(self):
        """Test no override occurs without override == True
        """
        graph = DeltaGraph()
        body_1 = PythonBody(tags=["preferred_1"])
        body_2 = PythonBody(tags=["preferred_2"])
        test_node = RealNode(graph, [body_1, body_2])

        test_node.select_body(preferred=["preferred_1"])
        self.assertEqual(test_node.body, body_1)

        test_node.select_body(preferred=["preferred_2"], override=False)
        self.assertEqual(test_node.body, body_1)

        test_node.select_body(preferred=["preferred_2"])
        self.assertEqual(test_node.body, body_2)

    def test_selection_exclusion_preference(self):
        """Test that selection works correctly with respect to body order,
        exclusions and preferences
        """
        graph = DeltaGraph()
        body_1 = PythonBody(tags=["exclude_me", "prefer_me"])
        body_2 = PythonBody()
        body_3 = PythonBody(tags=["prefer_me"])
        test_node = RealNode(graph, [body_1, body_2, body_3])

        test_node.select_body(exclusions=["exclude_me"])
        self.assertEqual(test_node.body, body_2)

        test_node.select_body(exclusions=["exclude_me"],
                              preferred=["prefer_me"])
        self.assertEqual(test_node.body, body_3)

    def test_no_bodies_node(self):
        """Test if no-body nodes throw errors on body access
        """
        graph = DeltaGraph()
        test_node = RealNode(graph, [])

        with self.assertRaises(ValueError):
            test_node.select_body()
            test_node.body

        body_1 = PythonBody(tags=["exclude_me"])
        body_2 = PythonBody(tags=["exclude_me"])
        test_node = RealNode(graph, [body_1, body_2])

        with self.assertRaises(ValueError):
            test_node.select_body(exclusions=["exclude_me"])
            test_node.body

    def test_class_as_tag(self):
        """Test classes can be used as tags
        """
        graph = DeltaGraph()
        body_1 = PythonBody()
        body_2 = PyFuncBody(lambda: False)
        test_node = RealNode(graph, [body_1, body_2])

        test_node.select_body(preferred=[PyFuncBody])
        self.assertEqual(test_node.body, body_2)

        with self.assertRaises(ValueError):
            test_node.select_body(exclusions=[PythonBody])
            test_node.body


if __name__ == "__main__":
    unittest.main()
