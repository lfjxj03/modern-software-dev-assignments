"""Pydantic models for /notes API contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NoteCreateRequest(BaseModel):
    """POST /notes request body."""

    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(
        ...,
        min_length=1,
        description=(
            "Note body text. Leading and trailing whitespace is stripped before validation."
        ),
    )


class NoteOut(BaseModel):
    """Note returned from POST /notes or GET /notes/{note_id}."""

    id: int
    content: str
    created_at: str = Field(..., description="ISO-like timestamp string from SQLite.")
