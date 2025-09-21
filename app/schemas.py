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
    confidence: Optional[float] = None
    extras: Dict[str, str] = Field(default_factory=dict)


class BOMResponseModel(BaseModel):
    items: List[BOMItemModel]
    detected_columns: List[str]
    metadata: Dict[str, Union[int, float, List[int], str]]


class FeedbackRatingModel(BaseModel):
    item: BOMItemModel
    correct: bool
    note: Optional[str] = None


class FeedbackRequestModel(BaseModel):
    document: Optional[str] = None
    ratings: List[FeedbackRatingModel]
    metadata: Optional[Dict[str, Union[int, float, List[int], str]]] = None


class FeedbackFeatureModel(BaseModel):
    feature: str
    label: str
    support: int
    success_rate: float


class FeedbackSummaryModel(BaseModel):
    total_feedback: int
    success_rate: float
    top_features: List[FeedbackFeatureModel]


class FeedbackResponseModel(BaseModel):
    status: str
    summary: FeedbackSummaryModel


__all__ = [
    "BOMItemModel",
    "BOMResponseModel",
    "FeedbackRatingModel",
    "FeedbackRequestModel",
    "FeedbackFeatureModel",
    "FeedbackSummaryModel",
    "FeedbackResponseModel",
]
