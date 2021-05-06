"""Helper functions for test.
"""

import os

import dill
from nbconvert.preprocessors import ExecutePreprocessor
import nbformat

import deltalanguage as dl


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
                body['python']['dillImpl']), dl.wiring.PythonBody))
            del body['python']['dillImpl']
        for tag in dill.loads(body['tags'])[:-1]:  # final tag is always object
            test_class.assertTrue(isinstance(tag, (str, type)))
        del body['tags']

    for node in g_capnp['nodes']:
        for port in node['inPorts'] + node['outPorts']:
            test_class.assertTrue(isinstance(
                dill.loads(port['type']), dl.data_types.BaseDeltaType))
            del port['type']
