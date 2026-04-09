from typing import Any

from pydantic import BaseModel, Field

from models.field_mapping import FieldMapping


class ExtractionResult(BaseModel):
    """Extraction result aligned with frontend TypeScript ExtractionResult interface.

    Frontend contract fields: fields, pdfPageCount, xsdFieldCount, processingTime.
    Extra generation fields (html, css, js, fidelityScore, etc.) are stored alongside
    and used by the generation panel — the frontend ignores unknown fields.
    """

    # Frontend contract
    fields: list[FieldMapping]
    pdfPageCount: int = 0
    xsdFieldCount: int = 0
    processingTime: float = 0.0

    # Extra fields for the generation panel (frontend accesses them at runtime)
    fidelityScore: float = 0.0
    fidelityComment: str = ""
    iaSuggestions: list[Any] = Field(default_factory=list)
    html: str = ""
    css: str = ""
    js: str = ""
    exemplo: str = ""
