from typing import Any, Literal, Optional

from pydantic import BaseModel


class Job(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "error"] = "pending"
    result: Optional[Any] = None
    error_msg: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
