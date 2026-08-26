"""
Data models for thyroid schema generation.
Enums for nodule positioning and dataclasses for geometry.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class VerticalLevel(Enum):
    SUPERIOR = "superior"
    MIDDLE = "middle"
    INFERIOR = "inferior"
    UNKNOWN = "unknown"


class DepthLevel(Enum):
    ANTERIOR = "anterior"
    POSTERIOR = "posterior"
    UNKNOWN = "unknown"


class LateralLevel(Enum):
    LATERAL = "lateral"
    MEDIAL = "medial"
    UNKNOWN = "unknown"


@dataclass
class NodulePosition:
    """Position and dimensions of a single nodule for schema rendering"""
    nodule_id: int              # 1, 2, 3...
    side: str                   # "RT" or "LT"
    vertical: VerticalLevel = VerticalLevel.UNKNOWN
    depth: DepthLevel = DepthLevel.UNKNOWN
    lateral: LateralLevel = LateralLevel.UNKNOWN
    is_isthmic: bool = False
    height_mm: float = 0.0     # Vertical dimension
    width_mm: float = 0.0      # Transverse dimension
    length_mm: float = 0.0     # AP dimension


@dataclass
class ThyroidGeometry:
    """Thyroid lobe dimensions for proportional rendering"""
    # Right lobe (mm)
    right_height: float = 45.0
    right_width: float = 15.0
    right_length: float = 15.0

    # Left lobe (mm)
    left_height: float = 45.0
    left_width: float = 15.0
    left_length: float = 15.0

    # Isthmus (mm)
    isthmus_thickness: float = 3.0
