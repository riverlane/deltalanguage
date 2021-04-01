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

from ._node_classes.abstract_node import AbstractNode, IndexProxyNode, ProxyNode
from ._node_classes.latency import Latency
from ._node_classes.migen_node import MigenNodeTemplate
from ._node_classes.node_bodies import (PyConstBody,
                                        PyFuncBody,
                                        PyInteractiveBody,
                                        PyMethodBody,
                                        PyMigenBody,
                                        PythonBody)
from ._node_classes.placeholder_node import PlaceholderNode
from ._node_classes.port_classes import InPort, OutPort
from ._node_classes.real_nodes import PythonNode, RealNode, as_node
from ._body_templates import InteractiveBodyTemplate
from ._node_templates import NodeTemplate
from ._decorators import (DeltaBlock,
                          DeltaMethodBlock,
                          Interactive)
from ._delta_graph import DeltaGraph
from ._placeholder_factory import placeholder_node_factory


# user-facing classes
__all__ = ["DeltaBlock",
           "DeltaMethodBlock",
           "Interactive",
           "DeltaGraph",
           "RealNode",
           "PythonNode",
           "MigenNodeTemplate",
           "placeholder_node_factory",
           "NodeTemplate"]
