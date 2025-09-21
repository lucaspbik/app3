"""Pydantic schemas for the API layer."""
from __future__ import annotations

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class BOMItemModel(BaseModel):
    position: Optional[str] = None
    part_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[Union[int, float]] = None
    unit: Optional[str] = None
    material: Optional[str] = None
    comment: Optional[str] = None
    extras: Dict[str, str] = Field(default_factory=dict)


class BOMResponseModel(BaseModel):
    items: List[BOMItemModel]
    detected_columns: List[str]
    metadata: Dict[str, Union[int, List[int], str]]


__all__ = ["BOMItemModel", "BOMResponseModel"]
