from typing import Iterable, Union, List
import numpy as np


def on_sphere_surface(point_a: Iterable[float], radius: float,
                      point_b: Union[Iterable[float], List[Iterable[float]]],
                      tolerance: float) -> bool:
    """
    Check if one or more points lie on the surface of a sphere centered at point_a.

    Args:
        point_a: Center of the sphere.
        radius: Radius of the sphere.
        point_b: A single point or a list of points to check.
        tolerance: Allowed deviation from the radius.

    Returns:
        True if all point(s) lie on the sphere surface within the tolerance.
    """
    def is_on_surface(p):
        return abs(np.linalg.norm(np.array(p) - np.array(point_a)) - radius) <= tolerance

    if isinstance(point_b[0], (float, int)):
        return is_on_surface(point_b)
    return all(is_on_surface(b) for b in point_b)
