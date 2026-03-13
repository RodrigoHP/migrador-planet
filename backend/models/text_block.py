from typing import Literal

from pydantic import BaseModel


class TextBlock(BaseModel):
    text: str
    x: float           # normalizado 0–1 (left)
    y: float           # normalizado 0–1 (top)
    width: float       # normalizado 0–1
    height: float      # normalizado 0–1
    page: int
    font_size: float = 0.0
    font_name: str = ""
    block_type: Literal["text", "table"] = "text"
