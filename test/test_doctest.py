import doctest
import os
import unittest


class TestDoctest(unittest.TestCase):

    def test_doctest(self):
        """Run doctest to test examples.

        Adapted from
        https://www.rosipov.com/blog/python-tests-with-doctest-and-unittest/
        """
        files = []
        root_dir = 'deltalanguage/'

        for root, _, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename == '__init__.py' or filename[-3:] != '.py':
                    continue
                f = os.path.join(root, filename)
                f = f.replace('/', '.')
                f = f[:-3]
                files.append(f)

        suite = unittest.TestSuite()
        for module in files:
            suite.addTest(doctest.DocTestSuite(module))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        # If errors or failures have occured, raise the first one
        if result.errors:
            raise AssertionError(result.errors[0][1])
        if result.failures:
            raise AssertionError(result.failures[0][1])


if __name__ == "__main__":
    unittest.main()
