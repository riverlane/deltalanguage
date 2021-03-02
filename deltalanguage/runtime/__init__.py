"""This submodule is dedicated to the runtime simulation as well as
universal routines used by Deltasimulator and Deltaruntime.

This submodule contains the following user-facing parts:

- Serialization routines:
  :py:func:`serialize_graph`
  :py:func:`deserialize_graph`
- Python Runtime Simulator :py:class:`DeltaPySimulator`

- Universal exit strategy :py:exc:`DeltaRuntimeExit`

For convenience the classes and functions listed above are also exposed to
the top level module and can be used like this:

.. code-block:: python

    import deltalanguage as dl

    print(dl.DeltaPySimulator())
    print(dl.DeltaRuntimeExit)
"""

from ._output import deserialize_graph, serialize_graph
from ._queues import ConstQueue, DeltaQueue
from ._runtime import DeltaPySimulator, DeltaRuntimeExit, DeltaThread


# user-facing classes
__all__ = ["deserialize_graph",
           "serialize_graph",
           "DeltaPySimulator",
           "DeltaRuntimeExit"]
