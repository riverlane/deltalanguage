"""Useful Blocks defined for testing purposes.
Also contains some common tests that can be checked in many situations as long
as there is a DeltaGraph
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
                                      DOptional,
                                      make_forked_return)
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


TwoIntsT, TwoInts = make_forked_return(
    {
        'x': int,
        'y': int
    }
)


@DeltaBlock()
def return_12() -> TwoIntsT:
    return TwoInts(1, 2)


@DeltaBlock(allow_const=False)
def return_12_non_const() -> TwoIntsT:
    return TwoInts(1, 2)


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


@Interactive([('n', int)], TwoIntsT)
def opt_increment(node: PythonNode):

    n = 0
    while n < 3:
        node.send(TwoInts(n, None))
        n = node.receive("n")

    node.send(TwoInts(None, n))


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


class MigenIncrementer(MigenNodeTemplate):
    """MigenIncrementer defines a simple node that increments by one a received message
    """

    def migen_body(self, template):
        # inputs and 1 output
        in1 = template.add_pa_in_port('in1', DOptional(int))
        out1 = template.add_pa_out_port('out1', DOptional(int))

        # Counter
        self.incremented = migen.Signal(10)

        # for instance, at this clock the node is ready to input
        self.comb += in1.ready.eq(1)

        self.sync += migen.If(
            out1.ready == 1,
            migen.If(in1.valid,
                     out1.data.eq(self.incremented),
                     out1.valid.eq(0x1),
                     self.incremented.eq(in1.data+1)
                     ).Else(out1.valid.eq(0))
        )
