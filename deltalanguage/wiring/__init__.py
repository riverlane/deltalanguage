"""
This submodule covers the essential bits about the constraction of the
Deltaflow graph and contains the following user-facing parts:

- :py:class:`DeltaGraph` is the central part of the Deltaflow language.

- Decorators used for quick node construction:
  :py:class:`DeltaBlock`
  :py:class:`DeltaMethodBlock`
  :py:class:`Interactive`

- Wiring routines:
  :py:func:`placeholder_node_factory`
  :py:func:`template_node_factory`

- Node classes 
  :py:class:`RealNode`
  :py:class:`PythonNode`

For convenience the classes and functions listed above are also exposed to
the top level module and can be used like this:

.. code-block:: python

    import deltalanguage as dl
    
    print(dl.DeltaGraph())
    print(dl.DeltaBlock())

The learning path for new user is best described in :doc:`tutorials/tutorials`.
"""

from ._node_classes.abstract_node import AbstractNode, ForkedNode, ProxyNode
from ._node_classes.latency import Latency
from ._node_classes.migen_node import MigenNodeTemplate
from ._node_classes.node_bodies import (PyConstBody,
                                        PyFuncBody,
                                        PyInteractiveBody,
                                        PyMethodBody,
                                        PythonBody,
                                        TemplateBody)
from ._node_classes.placeholder_node import PlaceholderNode
from ._node_classes.port_classes import InPort, OutPort
from ._node_classes.real_nodes import PythonNode, RealNode, as_node
from ._decorators import (DeltaBlock,
                          DeltaMethodBlock,
                          Interactive,
                          InteractiveProcess)
from ._delta_graph import DeltaGraph
from ._node_factories import py_method_node_factory, py_node_factory
from ._placeholder_factory import placeholder_node_factory
from ._template_factory import template_node_factory


# user-facing classes
__all__ = ["DeltaBlock",
           "DeltaMethodBlock",
           "Interactive",
           "DeltaGraph",
           "RealNode",
           "PythonNode",
           "TemplateBody",
           "MigenNodeTemplate",
           "placeholder_node_factory",
           "template_node_factory"]
