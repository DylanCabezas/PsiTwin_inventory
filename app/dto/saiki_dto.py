from typing import Any

from pydantic import BaseModel, Field


class SaikiAskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    id_inventario: str | None = None
    id_producto: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class SaikiAskResponse(BaseModel):
    answer: str
    model: str
    base_url: str
    source: str = "ollama"
    context: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
