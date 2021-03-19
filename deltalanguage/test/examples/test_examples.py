"""This test is meant for testing of all examples.
"""

import os
import subprocess
import unittest

from deltalanguage.test._utils import get_full_filelist, run_notebook


class TestTutorials(unittest.TestCase):
    """Test examples/tutorials.

    All files meant to have assertion statements.
    """

    def test_notebooks(self):
        filelist = get_full_filelist(
            os.path.join('examples', 'tutorials')
        )

        for file in filelist:
            if file.endswith('.ipynb'):
                print('running ' + file)
                _, errors = run_notebook(file)
                self.assertEqual(errors, [], msg=file + " failed")

    def test_scripts(self):
        filelist = get_full_filelist(
            os.path.join('examples', 'tutorials')
        )

        for file in filelist:
            if file.endswith('.py'):
                print('running ' + file)
                pipes = subprocess.Popen(['python', file],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                _, errors = pipes.communicate()
                for error in errors.decode("utf-8").split("\n"):
                    if error:
                        self.assertIn("[INFO]", error, msg=file + " failed")


class TestHardware(unittest.TestCase):
    """Test examples/hardware."""

    def test_dds_sine_wave(self):
        file = "examples/hardware/dds_sine_wave.ipynb"
        print('running ' + file)
        _, errors = run_notebook(file)
        self.assertEqual(errors, [], msg=file + " failed")


class TestVQE(unittest.TestCase):
    """Test examples/VQE."""

    def test_main(self):
        file = "examples/VQE/VQE_walkthrough.ipynb"
        print('running ' + file)
        _, errors = run_notebook(file)
        self.assertEqual(errors, [], msg=file + " failed")


class TestRabiDemo(unittest.TestCase):
    """Test examples/rabi_demo."""

    def test_main(self):
        filename = "examples/rabi_demo/run_test.py"
        print('running ' + filename)
        pipes = subprocess.Popen(['python', filename],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        _, errors = pipes.communicate()
        for error in errors.decode("utf-8").split("\n"):
            if error:
                self.assertTrue(("INFO" in error) or ("DEBUG" in error), error)

    def test_notebook(self):
        filename = "examples/rabi_demo/rabi_oscillation_walkthrough.ipynb"
        print('running ' + filename)
        _, errors = run_notebook(filename)
        self.assertEqual(errors, [], msg=filename + " failed")


class TestMicromotion(unittest.TestCase):
    """Test examples/demos/micromotion."""

    def test_migen_nodes(self):
        path = "examples/demos/micromotion/migen/"
        files = [
            "timestamper_model.py",
            "timestamper_interface.py",
            "DAC_controller.py"
        ]

        for file in files:
            errors = None
            filename = path + file
            print('running ' + filename)
            pipes = subprocess.Popen(['python', filename],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            _, errors = pipes.communicate()
            for error in errors.decode("utf-8").split("\n"):
                if error:
                    self.assertTrue(("INFO" in error) or (
                        "DEBUG" in error), error)



class TestCombTree(unittest.TestCase):
    """Test examples/comb_tree."""

    def test_main(self):
        filename = "examples/comb_tree/comb_tree.py"
        print('running ' + filename)
        pipes = subprocess.Popen(['python', filename],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        _, errors = pipes.communicate()
        for error in errors.decode("utf-8").split("\n"):
            if error:
                self.assertTrue(("INFO" in error) or ("DEBUG" in error), error)


if __name__ == '__main__':
    unittest.main()
