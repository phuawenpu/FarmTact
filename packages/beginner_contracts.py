"""Explicit inputs for the isolated, server-directed teaching season."""
from typing import Literal

from pydantic import Field

from packages.contracts import Strict


class CreateBeginnerJourney(Strict):
    name: str = Field(default='First harvest lesson', min_length=1, max_length=80)
    lesson_id: Literal['first_delivery', 'two_orders'] = 'first_delivery'


class BeginnerActionRequest(Strict):
    revision: int = Field(ge=0, strict=True)
    action_id: str = Field(min_length=1, max_length=64, pattern=r'^[a-z0-9_]+$')
    option_id: str | None = Field(default=None, min_length=1, max_length=100)
