"""
In order to facilitate data exchange between nodes written in potentially
different languages we use these intermediate data types to encode
to/from the data types used inside of the nodes.

This submodule contains the following user-facing parts:

- Primitive data types:
  :py:class:`Bool`
  :py:class:`Char`
  :py:class:`Int`
  :py:class:`UInt`
  :py:class:`Float`
  :py:class:`Complex`

- Compound data types:
  :py:class:`Array`
  :py:class:`Str`
  :py:class:`Tuple`
  :py:class:`Record`

- Special data types:
  :py:class:`Top`
  :py:class:`Raw`
  :py:class:`Union`
  :py:class:`Size`
  :py:class:`Optional`
  :py:class:`Void`

- Auxiliary functions:
  :py:func:`as_delta_type`
  :py:func:`delta_type`

For convenience the classes and functions listed above are also exposed to
the top level module and can be used like this:

.. code-block:: python

    import deltalanguage as dl

    print(dl.Bool())
    print(dl.delta_type(5))

More information about this submodule as well as examples of use can be
found in `Deltaflow Data Types <tutorials/data_types.html>`_.

"""

from ._delta_types import (BaseDeltaType,
                           PrimitiveDeltaType,
                           CompoundDeltaType,
                           Top,
                           Bool,
                           Char,
                           Complex,
                           Float,
                           Int,
                           Array,
                           Optional,
                           Raw,
                           Record,
                           Str,
                           Tuple,
                           UInt,
                           Union,
                           as_delta_type,
                           delta_type)
from ._exceptions import DeltaIOError, DeltaTypeError

from ._special import Size, Void

# user-facing classes
__all__ = ["Top",
           "Bool",
           "Char",
           "Int",
           "UInt",
           "Float",
           "Complex",
           "Array",
           "Str",
           "Tuple",
           "Record",
           "Raw",
           "Top",
           "Size",
           "Union",
           "Optional",
           "Void",
           "as_delta_type",
           "delta_type"]
