from typing import Any

from pydantic import BaseModel, Field, model_validator


class SaikiAskRequest(BaseModel):
    message: str | None = Field(default=None, min_length=1)
    question: str | None = Field(default=None, min_length=1)
    id_inventario: str | None = None
    id_producto: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_message(self):
        if not self.message and not self.question:
            raise ValueError("Debe indicar message o question.")
        if self.message and self.question and self.message != self.question:
            raise ValueError("message y question no pueden ser diferentes.")
        if not self.message:
            self.message = self.question
        return self


class SaikiAskResponse(BaseModel):
    answer: str
    model: str
    base_url: str
    source: str = "ollama"
    context: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    visualization: dict[str, Any] = Field(
        default_factory=lambda: {"type": "none"}
    )
    sources: list[str] = Field(default_factory=list)
