"""A collection of functions that allow simple casts from one type to another.
"""

from deltalanguage.data_types import DArray, DSize, DTuple, DUnion

from . import PyListOneCast, PyTupleOneCast, PythonBody, RealNode


def to_tuple_of_one(node: RealNode) -> RealNode:
    """Cast to tuple of one.

    Parameters
    ----------
    node : RealNode
        Node to cast.

    Returns
    -------
    RealNode
    """
    # Change return type
    org_t = node.return_type
    node.return_type = DTuple([org_t])

    # Change body to wrap output values into tuple
    org_body = node.body
    if not isinstance(org_body, PythonBody):
        raise ValueError("Casting only supported for python bodies.")
    node._body = PyTupleOneCast(org_body)

    return node


def to_list_of_one(node: RealNode) -> RealNode:
    """Cast to list with one element

    Parameters
    ----------
    node : RealNode
        Node to cast.

    Returns
    -------
    RealNode
    """
    # Change return type
    org_t = node.return_type
    node.return_type = DArray(org_t, DSize(1))

    # Change body to wrap output values into list
    org_body = node.body
    if not isinstance(org_body, PythonBody):
        raise ValueError("Casting only supported for python bodies.")
    node._body = PyListOneCast(org_body)

    return node


def to_union_of_one(node: RealNode) -> RealNode:
    """Cast to union of one.

    Parameters
    ----------
    node : RealNode
        Node to cast.

    Returns
    -------
    RealNode
    """
    org_t = node.return_type
    node.return_type = DUnion([org_t])

    return node
