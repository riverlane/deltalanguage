import unittest

import deltalanguage as dl


class DecoratorNoInputTypeTest(unittest.TestCase):
    """If input type is not provided in node definition error is raised."""

    def test_DeltaBlock(self):
        with self.assertRaises(TypeError):
            @dl.DeltaBlock()
            def foo(a) -> int:
                return a

    def test_DeltaMethodBlock(self):
        with self.assertRaises(TypeError):
            class _AClass:

                @dl.DeltaMethodBlock()
                def foo(self, a) -> int:
                    return a

    def test_Interactive(self):
        with self.assertRaises(ValueError):
            @dl.Interactive([('a')])
            def foo(node):
                node.receive("a")

    def test_MigenNodeTemplate(self):
        """This test will make more sense when migen nodes are created via
        decorators.
        """
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a')

        with self.assertRaises(TypeError):
            AMigenNode()


class DecoratorSetTagsTest(unittest.TestCase):
    """API test: tags can be provided to decorators during nodes definition or
    during the migen node initialization.
    """

    def test_DeltaBlock(self):
        @dl.DeltaBlock(allow_const = False, tags=['test_1'])
        def foo(a: int):
            print(a)

        with dl.DeltaGraph():
            node = foo(1)

        self.assertIn('test_1', node.body.access_tags)

    def test_DeltaMethodBlock(self):
        class AClass:

            @dl.DeltaMethodBlock(tags=['test_2'])
            def foo(self, a: int):
                print(a)

        with dl.DeltaGraph():
            node = AClass().foo(1)

        self.assertIn('test_2', node.body.access_tags)

    def test_Interactive(self):
        @dl.Interactive([('a', int)], tags=['test_3'])
        def foo(node):
            print(node.receive("a"))

        with dl.DeltaGraph():
            node = foo.call(a=1)

        self.assertIn('test_3', node.body.access_tags)

    def test_MigenNodeTemplate(self):
        """This test will make more sense when migen nodes are created via
        decorators.
        """
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', dl.DOptional(int))

        with dl.DeltaGraph():
            node = AMigenNode(tags=['test_4']).call(a=1)

        self.assertIn('test_4', node.body.access_tags)


class DecoratorNoOutputTypeTest(unittest.TestCase):
    """If output type is not provided in node definition Void is used."""

    def test_DeltaBlock(self):
        @dl.DeltaBlock()
        def foo(a: int):
            print(a)

        with dl.DeltaGraph():
            node = foo(1)

        self.assertEqual(node.outputs, dl.Void)

    def test_DeltaMethodBlock(self):
        class AClass:

            @dl.DeltaMethodBlock()
            def foo(self, a: int):
                print(a)

        with dl.DeltaGraph():
            node = AClass().foo(1)

        self.assertEqual(node.outputs, dl.Void)

    def test_Interactive(self):
        @dl.Interactive([("a", int)])
        def foo(node):
            print(node.receive("a"))

        self.assertEqual(foo.outputs, dl.Void)

    def test_MigenNodeTemplate(self):
        """This test will make more sense when migen nodes are created via
        decorators.
        """
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', dl.DOptional(int))

        self.assertEqual(AMigenNode()._outputs, dl.Void)


if __name__ == "__main__":
    unittest.main()
