from __future__ import annotations

__all__ = ("SanitizerReport",)

from pydantic import BaseModel

# TODO need to negotiate a sanitizer report format w/ UVA


class SanitizerReport(BaseModel):
    sanitizer: str  # FIXME: use an enum (is this even possible given the most recent DARPA example?)
