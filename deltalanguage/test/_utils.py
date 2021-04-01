"""Useful definitions for test suites only.

Please note that these definitions are also used in test suites of
Deltasimulator and Deltaruntime, thus if you do any changes make sure that
their tests are checked as well.

Also consider reorganizing this file and/or moving some routines to the
primitive library ``deltalanguage.lib.primitives``.
"""

import os
from typing import Any, List
import migen

import dill
from nbconvert.preprocessors import ExecutePreprocessor
import nbformat

from deltalanguage.data_types import (BaseDeltaType,
                                      Void,
                                      Top,
                                      Optional,
                                      UInt,
                                      Size)
from deltalanguage.lib.hal import command_creator
from deltalanguage.runtime import DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  DeltaMethodBlock,
                                  Interactive,
                                  MigenNodeTemplate,
                                  PythonBody,
                                  PythonNode)


def simple_graph():
    """Define a simple graph with just 2 nodes."""
    with DeltaGraph() as my_graph:
        one_int = return_4()
        printer(one_int)

    return my_graph


def simple_graph_forked():
    """Define a simple graph with just 3 nodes, one of each is forked."""
    with DeltaGraph() as my_graph:
        two_ints = return_12()
        printer(two_ints.x)
        printer(two_ints.y)

    return my_graph


def _no_duplicates(my_list: List[Any]) -> bool:
    """
    Parameters
    ----------
    my_list
        List to check.

    Returns
    -------
    bool
        True if there are no duplicate items in the given list.

    .. deprecated::
        Will be removed
    """
    return len(my_list) == len(set(my_list))


def _flatten(nested_list):
    """
    Parameters
    ----------
    nested_list
        List of lists.

    Returns
    -------
    Single list with all elements from the nested list.

    .. deprecated::
        Will be removed
    """
    return [item for l in nested_list for item in l]


def no_illegal_data_splitting(graph: DeltaGraph) -> bool:
    """
    Parameters
    ----------
    graph : DeltaGraph
        Graph to check.

    Returns
    -------
    bool
        True if no node has two out-ports with the same name.

    .. deprecated::
        Will be removed
    """
    out_ports_unique_by_node = [
        [_no_duplicates(out_port) for out_port in node.out_ports]
        for node in graph.nodes
    ]
    return all(_flatten(out_ports_unique_by_node))


def run_notebook(notebook_path, cleanup=True):
    """Helper script to run notebooks.

    Adapted with minor modifications from
    https://www.blog.pythonlibrary.org/2018/10/16/testing-jupyter-notebooks/
    """
    nb_name, _ = os.path.splitext(os.path.basename(notebook_path))
    dirname = os.path.dirname(notebook_path)

    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)

    proc = ExecutePreprocessor(timeout=600, kernel_name='python3')
    proc.allow_errors = True

    proc.preprocess(nb, {'metadata': {'path': '/'}})
    output_path = os.path.join(dirname, f'{nb_name}_all_output.ipynb')

    # temp file is created so as not to mess up the original notebook
    with open(output_path, mode='wt') as f:
        nbformat.write(nb, f)

    errors = []
    for cell in nb.cells:
        if 'outputs' in cell:
            for output in cell['outputs']:
                if output.output_type == 'error':
                    errors.append(output)

    if cleanup:
        os.remove(output_path)

    return nb, errors


def get_full_filelist(path):
    return [os.path.join(path, file) for file in os.listdir(path)]


def assert_capnp_content_types(test_class, g_capnp):
    """Helper function to check capnp has been deserialised correctly.

    Parameters
    ----------
    test_class:
        The test class calling the function
    g_capnp :
        The deserialised capnp graph
    """

    for body in g_capnp['bodies']:
        if 'python' in body:
            test_class.assertTrue(isinstance(dill.loads(
                body['python']['dillImpl']), PythonBody))
            del body['python']['dillImpl']
    for node in g_capnp['nodes']:
        for port in node['inPorts'] + node['outPorts']:
            test_class.assertTrue(isinstance(
                dill.loads(port['type']), BaseDeltaType))
            del port['type']


@DeltaBlock()
def add(n1: int, n2: int) -> int:
    return n1 + n2


@DeltaBlock(allow_const=False)
def add_non_const(n1: int, n2: int) -> int:
    return n1 + n2


@DeltaBlock(outputs=[('x', int), ('y', int)])
def return_12():
    return 1, 2


@DeltaBlock(outputs=[('x', int), ('y', int)], allow_const=False)
def return_12_non_const():
    return 1, 2


@DeltaBlock()
def return_4() -> int:
    return 4


@DeltaBlock()
def return_2() -> int:
    return 2


@DeltaBlock(allow_const=False)
def do_nothing(n: int) -> Void:
    pass


class OtherClass:
    def __init__(self, num: int):
        self.num = num

    @DeltaMethodBlock()
    def add_member(self, m: int) -> int:
        return m + self.num


@DeltaBlock(allow_const=False)
def return_1() -> int:
    return 1


@DeltaBlock(allow_const=False)
def printer(obj: Top) -> Void:
    if obj is not None:
        print(obj)


@DeltaBlock(allow_const=True)
def const_consumer(obj: Top) -> Void:
    pass


@Interactive([('n', int)], [('x', int), ('y', int)])
def opt_increment(node: PythonNode):

    n = 0
    while n < 3:
        node.send(n, None)
        n = node.receive("n")

    node.send(None, n)


@DeltaBlock(allow_const=False)
def add1_or0(n: int) -> int:
    return n + 1


class SomeClass:
    def __init__(self):
        self.n = 0

    @DeltaMethodBlock(name="methodnode")
    def method(self) -> int:
        self.n += 1
        return self.n


@DeltaBlock(allow_const=False)
def err_if_3(n: int) -> Void:
    if n == 3:
        raise Exception("oh no! n is 3!!!")


@DeltaBlock()
def async_err_if_4(n: int) -> Void:
    if n == 4:
        raise Exception("oh no! n is 3!!!")


class InputSummer:

    def __init__(self):
        self.sum = 0

    @DeltaMethodBlock()
    def sum_all(self, item: int) -> int:
        self.sum += item
        return self.sum


class InputChecker:
    """Compares one input vs a user provided condition
    """

    def __init__(self, condition):
        self.condition = condition
        self.cond_met = False

    @DeltaMethodBlock()
    def check(self, item: object) -> object:
        if item:
            if self.condition(item):
                self.cond_met = True
                raise DeltaRuntimeExit
            else:
                return item


class InputCheckerWithExit(InputChecker):
    """Compares one input vs a user provided condition and exits if matches
    """
    @DeltaMethodBlock()
    def check(self, item: object) -> object:
        if item:
            if self.condition(item):
                self.cond_met = True
                raise DeltaRuntimeExit
            else:
                return item


class DUT1(MigenNodeTemplate):

    def migen_body(self, template):
        # I/O:
        i1 = template.add_pa_in_port("i1", Optional(int))
        o1 = template.add_pa_out_port("o1", int)

        # LOGIC:
        self.counter = migen.Signal(1000)
        self.sync += self.counter.eq(self.counter + 1)

        # Two memories for testing
        self.specials.mem1 = mem1 = migen.Memory(32, 100, init=[5, 15, 32])
        read_port1 = mem1.get_port()
        self.specials.mem2 = mem2 = migen.Memory(32, 100, init=[2, 4, 6, 8])
        read_port2 = mem2.get_port()
        self.specials += read_port1
        self.specials += read_port2
        self.mem_out1 = migen.Signal(32)
        self.mem_out2 = migen.Signal(32)

        self.sync += (read_port1.adr.eq(self.counter),
                      self.mem_out1.eq(read_port1.dat_r))

        self.sync += (read_port2.adr.eq(self.counter),
                      self.mem_out2.eq(read_port2.dat_r))

        # DEBUGGING:
        # add any signal you want to see in debugging and printing format
        # (in_ports, out_ports, inputs, output are added by default):
        self.debug_signals = {'counter': (self.counter, '05b')}

        self.comb += migen.If(
            self.counter >= 5,
            i1.ready.eq(1)
        )

        self.comb += migen.If(
            o1.ready == 1,
            migen.If(
                self.counter == 10,
                o1.data.eq(self.counter+i1.data),
                o1.valid.eq(1)
            ).Else(
                o1.valid.eq(0)
            )
        )


class MigenIncrementer(MigenNodeTemplate):

    def migen_body(self, template):
        # I/O:
        i1 = template.add_pa_in_port("i1", Optional(int))
        o1 = template.add_pa_out_port("o1", int)

        self.comb += (
            i1.ready.eq(1),
        )

        started = migen.Signal(1)

        self.sync += migen.If(
            i1.valid == 1,
            o1.valid.eq(1),
            o1.data.eq(i1.data+1)
        ).Else(
            o1.data.eq(0),
            migen.If(started == 0,
                     o1.valid.eq(1),
                     started.eq(1)
                     ).Else(
                o1.valid.eq(0)
            )
        )


@Interactive([("measurement", UInt(Size(32)))],
             [("output", UInt(Size(32)))],
             name="interactive_simple")
def send_gates_list_then_exit(node: PythonNode):
    cmds = ["RX", "RZ", "RY"]
    # for non-deterministic tests use random.randint(0, 255)
    args = [99, 250, 11]

    node.send(command_creator("STATE_PREPARATION"))

    for cmd, arg in zip(cmds, args):
        node.send(command_creator(cmd, argument=arg))
    node.send(command_creator("STATE_MEASURE"))

    measurement = node.receive("measurement")
    print(f"Measurement: {measurement}")

    raise DeltaRuntimeExit


class TripleStateSaver:

    def __init__(self, count: int):
        self.max_count = count
        self.curr_count = 0

        self.x_store = []
        self.y_store = []
        self.z_store = []

    @DeltaMethodBlock()
    def multi_count_print_exit(self,
                               x: Optional(int),
                               y: Optional(int),
                               z: Optional(bool)):
        """Count and store messages until we receive self.max_count many, then 
        print all stores and exit.
        """
        if x is not None:
            self.x_store.append(x)
            self.curr_count += 1

        if y is not None:
            self.y_store.append(y)
            self.curr_count += 1

        if z is not None:
            self.z_store.append(z)
            self.curr_count += 1

        if self.curr_count >= self.max_count:
            print(self.x_store)
            print(self.y_store)
            print(self.z_store)
            raise DeltaRuntimeExit
