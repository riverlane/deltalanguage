import unittest

from deltalanguage._utils import NamespacedName, QueueMessage


class NamespacedNameTest(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(NamespacedName("a", "b")), "a.b")
        self.assertEqual(str(NamespacedName("a", None)), "a")

        with self.assertRaises(TypeError):
            NamespacedName("a")

        with self.assertRaises(TypeError):
            NamespacedName()

    def test_eq(self):
        self.assertEqual(NamespacedName("a", "b"),
                         NamespacedName("a", "b"))

        self.assertEqual(NamespacedName("a", None),
                         NamespacedName("a", None))

        self.assertNotEqual(NamespacedName("a", "b"),
                            NamespacedName("a", None))


class QueueMessageTest(unittest.TestCase):

    def test_eq(self):
        self.assertEqual(QueueMessage("test", 5),
                         QueueMessage("test", 5))

        self.assertEqual(QueueMessage("test", 5),
                         QueueMessage("test", 1))

        self.assertNotEqual(QueueMessage("test1", 6),
                            QueueMessage("test2", 6))

        self.assertEqual(hash(QueueMessage("blah-blah", 6)),
                         hash("blah-blah"))


if __name__ == "__main__":
    unittest.main()
