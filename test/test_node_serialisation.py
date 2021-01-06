import math
import subprocess
import unittest

import dill

from deltalanguage.data_types import NoMessage
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  DeltaMethodBlock,
                                  PyConstBody,
                                  PyFuncBody,
                                  PyMethodBody)

from test._utils import return_2


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

        node_indepentent_const = graph.nodes[2]
        node_indepentent_func = graph.nodes[5]
        node_method = graph.nodes[7]
        node_env_func = graph.nodes[10]

        # const independent func
        self.serialised_indepentent_const =\
            node_indepentent_const.get_serialised_body()
        self.deserialised_node_indepentent_const = dill.loads(
            self.serialised_indepentent_const
        )

        # non-const independent func with environment
        self.serialised_env_func =\
            node_env_func.get_serialised_body()

        # non-const independent func
        self.serialised_indepentent_func =\
            node_indepentent_func.get_serialised_body()
        self.deserialised_node_indepentent_func = dill.loads(
            self.serialised_indepentent_func
        )

        # method
        self.serialised_method = node_method.get_serialised_body()
        self.deserialised_node_method = dill.loads(
            self.serialised_method
        )

    def test_deserialisation(self):
        self.assertEqual(
            type(self.deserialised_node_indepentent_const),
            PyConstBody
        )
        self.assertEqual(
            type(self.deserialised_node_indepentent_func),
            PyFuncBody
        )
        self.assertEqual(
            type(self.deserialised_node_method),
            PyMethodBody
        )

    def test_load_new_environment_independent_const(self):

        # build up python script to run in seperate environment
        python_string = "import dill\n"
        python_string += "deserialised_node_body = "
        python_string += f"dill.loads({self.serialised_indepentent_const})\n"
        python_string += "print(deserialised_node_body.eval())"

        # begin python process in seperate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(7, int(output))

    def test_load_new_environment_independent_nonconst(self):

        # build up python script to run in seperate environment
        python_string = "import dill\n"
        python_string += "deserialised_node_body = "
        python_string += f"dill.loads({self.serialised_indepentent_func})\n"
        python_string += "print(deserialised_node_body.eval(5, 4))"

        # begin python process in seperate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(9, int(output))

    def test_load_new_environment_env_func(self):

        # build up python script to run in seperate environment
        python_string = "import dill\n"
        python_string += "deserialised_node_body = "
        python_string += f"dill.loads({self.serialised_env_func})\n"
        python_string += "print(deserialised_node_body.eval(14, 21))"

        # begin python process in seperate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(7, int(output))

    def test_load_new_environment_method(self):

        # build up python script to run in seperate environment
        python_string = "import dill\n"
        python_string += "deserialised_node_body = "
        python_string += f"dill.loads({self.serialised_method})\n"
        python_string += "print(deserialised_node_body.eval(3))"

        # begin python process in seperate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(5, int(output))

    def test_load_and_runtime_new_environment_independent_const(self):

        # build up python script to run in seperate environment
        python_string = """
import dill

from deltalanguage.data_types import NoMessage
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import DeltaBlock, DeltaGraph

@DeltaBlock(name="add")
def add(a: int, b: int) -> int:
    return a + b


@DeltaBlock(name="print_exit", allow_const=False)
def print_then_exit(to_print: object) -> NoMessage:
    print(to_print)
    raise DeltaRuntimeExit


with DeltaGraph() as graph:
    added = add(a=4, b=3)
    print_then_exit(to_print=added)
"""

        python_string += f"""deserialised_node = dill.loads({self.serialised_indepentent_const})

graph.nodes[2]._body = deserialised_node

rt = DeltaPySimulator(graph)
rt.run()

"""

        # begin python process in seperate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(7, int(output))

    def test_load_and_runtime_new_environment_env_func(self):

        # build up python script to run in seperate environment
        python_string = """
import dill

from deltalanguage.data_types import NoMessage
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import DeltaBlock, DeltaGraph

@DeltaBlock(name="add", allow_const=False)
def add(a: int, b: int) -> int:
    return a + b


@DeltaBlock(name="print_exit", allow_const=False)
def print_then_exit(to_print: object) -> NoMessage:
    print(to_print)
    raise DeltaRuntimeExit


with DeltaGraph() as graph:
    added = add(a=14, b=21)
    print_then_exit(to_print=added)
"""

        python_string += f"""deserialised_node = dill.loads({self.serialised_env_func})

graph.nodes[2]._body = deserialised_node

rt = DeltaPySimulator(graph)
rt.run()

"""

        # begin python process in seperate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(7, int(output))

    def test_load_and_runtime_new_environment_method(self):

        # build up python script to run in seperate environment
        python_string = """
import dill

from deltalanguage.data_types import NoMessage
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import DeltaBlock, DeltaMethodBlock, DeltaGraph

class Adder:

    def __init__(self, x: int):
        self._x = x

    @DeltaMethodBlock(name="add_x")
    def add_x(self, a: int) -> int:
        return a + self._x


@DeltaBlock(name="print_exit", allow_const=False)
def print_then_exit(to_print: object) -> NoMessage:
    print(to_print)
    raise DeltaRuntimeExit

add_2 = Adder(2)

with DeltaGraph() as graph:
    added_2 = add_2.add_x(a=3)
    print_then_exit(to_print=added_2)
"""

        python_string += f"""deserialised_node = dill.loads({self.serialised_method})

graph.nodes[1]._body = deserialised_node

rt = DeltaPySimulator(graph)
rt.run()

"""

        # begin python process in seperate environment
        p = subprocess.run(
            [r"python"],
            input=str.encode(python_string),
            stdout=subprocess.PIPE,
            check=False
        )
        output = p.stdout.decode()

        self.assertEqual(5, int(output))


class StateSaverSerialisationTest(unittest.TestCase):

    def test_serialise_state_saver(self):
        """Serialise a state saver and load it in a new instance."""
        saver = StateSaver(t=int, verbose=True)
        with DeltaGraph() as test_graph:
            saver_node = saver.save(return_2())
        saver_body = saver_node.get_serialised_body()
        python_string = f"""
import dill
saver_body = dill.loads({saver_body})
saver_body.eval(5)
"""
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
