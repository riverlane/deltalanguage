import math
import subprocess
import textwrap
import unittest

import dill

from deltalanguage.lib import StateSaver
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  DeltaMethodBlock,
                                  PyConstBody,
                                  PyFuncBody,
                                  PyMethodBody)

from deltalanguage.test._node_lib import return_2_const


class Adder:

    def __init__(self, x: int):
        self._x = x

    @DeltaMethodBlock(name="add_x")
    def add_x(self, a: int) -> int:
        return a + self._x


class NodeSerialisationTest(unittest.TestCase):

    def setUp(self):

        @DeltaBlock(name="add_const")
        def add_const(a: int, b: int) -> int:
            return a + b

        @DeltaBlock(name="add_func", allow_const=False)
        def add_func(a: int, b: int) -> int:
            return a + b

        @DeltaBlock(name="gcd", allow_const=False)
        def gcd(a: int, b: int) -> int:
            return math.gcd(a, b)

        add_2 = Adder(2)

        with DeltaGraph() as graph:
            add_const(a=4, b=3)
            add_func(a=5, b=4)
            add_2.add_x(a=3)
            gcd(a=14, b=7)

        node_independent_const = graph.nodes[2]
        node_independent_func = graph.nodes[5]
        node_method = graph.nodes[7]
        node_env_func = graph.nodes[10]

        # const independent func
        self.serialized_independent_const =\
            node_independent_const.body.as_serialized
        self.deserialized_node_independent_const = dill.loads(
            self.serialized_independent_const
        )

        # non-const independent func with environment
        self.serialized_env_func =\
            node_env_func.body.as_serialized

        # non-const independent func
        self.serialized_independent_func =\
            node_independent_func.body.as_serialized
        self.deserialized_node_independent_func = dill.loads(
            self.serialized_independent_func
        )

        # method
        self.serialized_method = node_method.body.as_serialized
        self.deserialized_node_method = dill.loads(
            self.serialized_method
        )

    def test_deserialization(self):
        self.assertEqual(
            type(self.deserialized_node_independent_const),
            PyConstBody
        )
        self.assertEqual(
            type(self.deserialized_node_independent_func),
            PyFuncBody
        )
        self.assertEqual(
            type(self.deserialized_node_method),
            PyMethodBody
        )

    def test_load_new_environment_independent_const(self):

        # build up python script to run in separate environment
        python_string = "import dill\n"
        python_string += "deserialized_node_body = "
        python_string += f"dill.loads({self.serialized_independent_const})\n"
        python_string += "print(deserialized_node_body.eval())"

        # begin python process in separate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(7, int(output))

    def test_load_new_environment_independent_nonconst(self):

        # build up python script to run in separate environment
        python_string = "import dill\n"
        python_string += "deserialized_node_body = "
        python_string += f"dill.loads({self.serialized_independent_func})\n"
        python_string += "print(deserialized_node_body.eval(5, 4))"

        # begin python process in separate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(9, int(output))

    def test_load_new_environment_env_func(self):

        # build up python script to run in separate environment
        python_string = "import dill\n"
        python_string += "deserialized_node_body = "
        python_string += f"dill.loads({self.serialized_env_func})\n"
        python_string += "print(deserialized_node_body.eval(14, 21))"

        # begin python process in separate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(7, int(output))

    def test_load_new_environment_method(self):

        # build up python script to run in separate environment
        python_string = "import dill\n"
        python_string += "deserialized_node_body = "
        python_string += f"dill.loads({self.serialized_method})\n"
        python_string += "print(deserialized_node_body.eval(3))"

        # begin python process in separate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(5, int(output))

    def test_load_and_runtime_new_environment_independent_const(self):

        # build up python script to run in separate environment
        python_string = textwrap.dedent(
            """
            import dill

            from deltalanguage.data_types import Void
            from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
            from deltalanguage.wiring import DeltaBlock, DeltaGraph

            @DeltaBlock(name="add")
            def add(a: int, b: int) -> int:
                return a + b


            @DeltaBlock(name="print_exit", allow_const=False)
            def print_then_exit(to_print: object) -> Void:
                print(to_print)
                raise DeltaRuntimeExit


            with DeltaGraph() as graph:
                added = add(a=4, b=3)
                print_then_exit(to_print=added)
            """
        )

        python_string += textwrap.dedent(
            f"""
            deserialized_node = dill.loads({self.serialized_independent_const})

            graph.nodes[2]._body = deserialized_node

            rt = DeltaPySimulator(graph)
            rt.run()
            """
        )

        # begin python process in separate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(7, int(output))

    def test_load_and_runtime_new_environment_env_func(self):

        # build up python script to run in separate environment
        python_string = textwrap.dedent(
            """
            import dill

            from deltalanguage.data_types import Void
            from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
            from deltalanguage.wiring import DeltaBlock, DeltaGraph

            @DeltaBlock(name="add", allow_const=False)
            def add(a: int, b: int) -> int:
                return a + b


            @DeltaBlock(name="print_exit", allow_const=False)
            def print_then_exit(to_print: object) -> Void:
                print(to_print)
                raise DeltaRuntimeExit


            with DeltaGraph() as graph:
                added = add(a=14, b=21)
                print_then_exit(to_print=added)
            """
        )

        python_string += textwrap.dedent(
            f"""
            deserialized_node = dill.loads({self.serialized_env_func})

            graph.nodes[2]._body = deserialized_node

            rt = DeltaPySimulator(graph)
            rt.run()
            """
        )

        # begin python process in separate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(7, int(output))

    def test_load_and_runtime_new_environment_method(self):

        # build up python script to run in separate environment
        python_string = textwrap.dedent(
            """
            import dill

            from deltalanguage.data_types import Void
            from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
            from deltalanguage.wiring import DeltaBlock, DeltaMethodBlock, DeltaGraph

            class Adder:

                def __init__(self, x: int):
                    self._x = x

                @DeltaMethodBlock(name="add_x")
                def add_x(self, a: int) -> int:
                    return a + self._x


            @DeltaBlock(name="print_exit", allow_const=False)
            def print_then_exit(to_print: object) -> Void:
                print(to_print)
                raise DeltaRuntimeExit

            add_2 = Adder(2)

            with DeltaGraph() as graph:
                added_2 = add_2.add_x(a=3)
                print_then_exit(to_print=added_2)
            """
        )

        python_string += textwrap.dedent(
            f"""
            deserialized_node = dill.loads({self.serialized_method})

            graph.nodes[1]._body = deserialized_node

            rt = DeltaPySimulator(graph)
            rt.run()
            """
        )

        # begin python process in separate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(5, int(output))


class StateSaverSerialisationTest(unittest.TestCase):

    def test_serialize_state_saver(self):
        """Serialise a state saver and load it in a new instance."""
        saver = StateSaver(t=int, verbose=True)
        with DeltaGraph():
            saver_node = saver.save(return_2_const())
        saver_body = saver_node.body.as_serialized
        python_string = textwrap.dedent(
            f"""
            import dill
            saver_body = dill.loads({saver_body})
            saver_body.eval(5)
            """
        )
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(output, "saving 5\n")


if __name__ == "__main__":
    unittest.main()
