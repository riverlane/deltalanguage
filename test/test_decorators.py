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
        with self.assertRaises(TypeError):
            @dl.Interactive({'a'})
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


class DecoratorNoOutputTypeTest(unittest.TestCase):
    """If output type is not provided in node definition Void is used."""

    def test_DeltaBlock(self):
        @dl.DeltaBlock()
        def foo(a: int):
            print(a)

        with dl.DeltaGraph():
            node = foo(1)

        self.assertEqual(node.out_type, dl.Void)

    def test_DeltaMethodBlock(self):
        class AClass:

            @dl.DeltaMethodBlock()
            def foo(self, a: int):
                print(a)

        with dl.DeltaGraph():
            node = AClass().foo(1)

        self.assertEqual(node.out_type, dl.Void)

    def test_Interactive(self):
        @dl.Interactive({"a": int})
        def foo(node):
            print(node.receive("a"))

        self.assertEqual(foo.out_type, dl.Void)

    def test_MigenNodeTemplate(self):
        """This test will make more sense when migen nodes are created via
        decorators.
        """
        class AMigenNode(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('a', dl.DOptional(int))

        self.assertEqual(AMigenNode()._out_type, dl.Void)


if __name__ == "__main__":
    unittest.main()
