from typing import List


def generate_angles(resolution: int, register_width: int = 10) -> List[int]:
    """Creates a list of rotation angles.
    Resolution defined in bits mapped to the bit width of the register.

    Parameters
    ----------
    resolution : int
        The required resolution between 0 and 2pi between angle values.
    register_width : int, optional
        The number of bits to encode the angles onto, by default 10

    Returns
    -------
    List[int]
        A list of integers encoding angles between 0 and 2pi on a number of
        bits equal to the register_width.

    Raises
    ------
    ValueError
        If the resolution required exceeds the register width available.
    """
    if resolution > register_width:
        raise ValueError(
            f"Resolution ({resolution}) can not be greater than " +
            f"register width ({register_width})!"
        )

    scaling = (2**register_width) / (2**resolution)

    angles = []
    for i in range(0, 2**resolution):
        angles.append(int(i * scaling))
    return angles
