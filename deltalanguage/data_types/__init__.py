"""Deltaflow data type system.

An extensive overview can be found in
`Deltaflow Data Types <tutorials/data_types.html>`_.

.. TODO:: When that file is reviewed bring here a single paragraph summary.
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
                           DSize,
                           DStr,
                           DTuple,
                           DUInt,
                           DUnion,
                           ForkedReturn,
                           as_delta_type,
                           delta_type,
                           make_forked_return)
from ._exceptions import (DeltaIOError,
                          DeltaTypeError,
                          NoMessage)
