import uuid
from typing import Literal

from pydantic import BaseModel, Field


class FieldMapping(BaseModel):
    """Field mapping aligned with frontend TypeScript FieldMapping interface."""

    # Frontend contract fields (camelCase to match TypeScript interface)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pdfText: str = ""
    jsonPath: str = ""
    type: Literal["text", "date", "currency", "list", "composite"] = "text"
    confidence: Literal["high", "medium", "low"] = "low"
    status: Literal["ok", "ambiguous", "not_found", "optional"] = "not_found"
    candidates: list[str] | None = None
    isManual: bool = False
    pageRef: int | None = None
    boundingBox: dict[str, float] | None = None

    # Backend-only fields used by TemplateGenerator / FidelityScorer
    raw_confidence: float = 0.0
    data_value: str = ""
    xsd_type: str = "string"
    normalized_value: str = ""
