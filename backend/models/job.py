from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Job(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_id: str
    status: Literal["pending", "running", "done", "error"] = "pending"
    result: Any | None = None
    error_msg: str | None = None
