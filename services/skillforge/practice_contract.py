
from typing import Literal

from pydantic import BaseModel, Field


class Submission(BaseModel):
    problem: str = Field(min_length=1, max_length=60)
    language: Literal["python", "javascript"]
    code: str = Field(min_length=1, max_length=24_000)
    examples_only: bool = False
