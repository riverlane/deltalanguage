"""
The standard library for the Deltaflow language contains:

- Primitives for generation, re-routing, and collection of data:
  :py:func:`make_generator`
  :py:func:`make_splitter`
  :py:class:`StateSaver`
"""

from deltalanguage.lib.primitives import (make_generator,
                                          make_splitter,
                                          StateSaver)
