"""
Inspection data structures for the engineering workbench.
"""
from dataclasses import dataclass, field
from typing import Any, Optional, Union


@dataclass
class MeasurementItem:
    """A single measurement or inspection result."""

    item_id: str
    group_id: str
    name: str
    measurement_type: str
    value: float
    unit: str = "model units"
    visible: bool = True
    highlighted: bool = False
    points: list[list[float]] = field(default_factory=list)
    vertex_ids: list[int] = field(default_factory=list)
    face_id: Optional[int] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class InspectionGroup:
    """A named collection of measurement items."""

    group_id: str
    name: str
    visible: bool = True
    item_ids: list[str] = field(default_factory=list)


@dataclass
class SelectionState:
    """Current selected inspection object."""

    selection_type: Optional[str] = None
    object_id: Optional[Union[str, int]] = None
    label: str = ""
    data: dict[str, Any] = field(default_factory=dict)
