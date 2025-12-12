"""Coordinate transformation utility functions."""

import numpy as np
from typing import Union, Sequence, overload


@overload
def convert_longitudes(longitude: float, conversion_type: str) -> float:
    ...


@overload
def convert_longitudes(longitude: int, conversion_type: str) -> float:
    ...


@overload
def convert_longitudes(longitude: Sequence[float], conversion_type: str) -> np.ndarray:
    ...


@overload
def convert_longitudes(longitude: np.ndarray, conversion_type: str) -> np.ndarray:
    ...


def convert_longitudes(
    longitude: Union[float, int, Sequence[float], np.ndarray],
    conversion_type: str
) -> Union[float, np.ndarray]:
    """Converts longitudes from -180/180 to 0/360 scale and vice versa.

    Args:
        longitude (Union[float, int, Sequence[float], np.ndarray]): The longitude(s).
        conversion_type (str): The conversion type ('to_360' or 'to_180').

    Returns:
        Union[float, np.ndarray]: The converted longitude(s).
        
    Raises:
        ValueError: If conversion_type is not 'to_360' or 'to_180'.
    """
    if conversion_type not in {"to_360", "to_180"}:
        raise ValueError("Conversion type must be 'to_360' or 'to_180'.")

    is_scalar = isinstance(longitude, (float, int))
    lon_array = np.asarray(longitude, dtype=float)

    if conversion_type == "to_360":
        result = (lon_array + 360) % 360
    else:
        result = ((lon_array + 180) % 360) - 180
    
    return result.item() if is_scalar else result


def convert_lon_range(
    lon_range: tuple[float, float],
    conversion_type: str
) -> tuple[float, float]:
    """Converts a longitude range between -180/180 and 0/360 scales.

    Args:
        lon_range (tuple[float, float]): The longitude range.
        conversion_type (str): The conversion type ('to_360' or 'to_180').

    Returns:
        tuple[float, float]: The converted longitude range.
        
    Raises:
        ValueError: If conversion_type is not 'to_360' or 'to_180'.
    """
    if conversion_type not in {"to_360", "to_180"}:
        raise ValueError("Conversion type must be 'to_360' or 'to_180'.")
    
    min_lon, max_lon = lon_range

    if max_lon - min_lon >= 360 - 1e-6:
        return (-180.0, 180.0) if conversion_type == "to_180" else (0.0, 360.0)

    return (
        convert_longitudes(min_lon, conversion_type),
        convert_longitudes(max_lon, conversion_type),
    )
