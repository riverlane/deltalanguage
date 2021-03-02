"""
In order to facilitate data exchange between nodes written in potentially
different languages we use these intermediate data types to encode
to/from the data types used inside of the nodes.

This submodule contains the following user-facing parts:

- Primitive data types:
  :py:class:`DBool`
  :py:class:`DChar`
  :py:class:`DInt`
  :py:class:`DUInt`
  :py:class:`DFloat`
  :py:class:`DComplex`

- Compound data types:
  :py:class:`DArray`
  :py:class:`DStr`
  :py:class:`DTuple`
  :py:class:`DRecord`

- Special data types:
  :py:class:`Top`
  :py:class:`DRaw`
  :py:class:`DUnion`
  :py:class:`DSize`
  :py:class:`DOptional`
  :py:class:`Void`

- Auxiliary functions:
  :py:func:`make_forked_return`
  :py:func:`as_delta_type`
  :py:func:`delta_type`

For convenience the classes and functions listed above are also exposed to
the top level module and can be used like this:

.. code-block:: python

    import deltalanguage as dl
    
    print(dl.DBool())
    print(dl.delta_type(5))

More information about this submodule as well as examples of use can be
found in `Deltaflow Data Types <tutorials/data_types.html>`_.

"""

from ._delta_types import (BaseDeltaType,
                           PrimitiveDeltaType,
                           CompoundDeltaType,
                           Top,
                           DBool,
                           DChar,
                           DComplex,
                           DFloat,
                           DInt,
                           DArray,
                           DOptional,
                           DRaw,
                           DRecord,
                           DStr,
                           DTuple,
                           DUInt,
                           DUnion,
                           ForkedReturn,
                           as_delta_type,
                           delta_type,
                           make_forked_return)
from ._exceptions import DeltaIOError, DeltaTypeError
                          
from ._special import DSize, Void

# user-facing classes
__all__ = ["Top",
           "DBool",
           "DChar",
           "DInt",
           "DUInt",
           "DFloat",
           "DComplex",
           "DArray",
           "DStr",
           "DTuple",
           "DRecord",
           "DRaw",
           "Top",
           "DSize",
           "DUnion",
           "DOptional",
           "Void",
           "make_forked_return",
           "as_delta_type",
           "delta_type"]
