from typing import Any, Literal

from pydantic import BaseModel


class Job(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "error"] = "pending"
    result: Any | None = None
    error_msg: str | None = None

    class Config:
        arbitrary_types_allowed = True
