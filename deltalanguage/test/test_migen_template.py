import unittest

import deltalanguage as dl


class MigenNodeTemplateTest(unittest.TestCase):
    """"Tests only relevant for MigenNodeTemplate."""

    def test_optional_input(self):
        """Only optional inputs are supported."""

        class AMigenNodeA(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('in1', int)

        class AMigenNodeB(dl.MigenNodeTemplate):
            def migen_body(self, template):
                template.add_pa_in_port('in1', dl.DOptional(int))

        with self.assertRaises(dl.data_types.DeltaTypeError):
            AMigenNodeA()

        AMigenNodeB()

if __name__ == "__main__":
    unittest.main()
