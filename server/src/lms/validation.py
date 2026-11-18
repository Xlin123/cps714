"""One shape for every request-validation error, with messages fit to show users.

FastAPI's default 422 body lists pydantic's raw errors, wording them for
developers and echoing each rejected ``input`` back, passwords included. The
handler here replaces it with ``{"detail": "VALIDATION_FAILED", "errors":
[{"field": ..., "message": ...}]}`` and never includes the submitted values.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

VALIDATION_FAILED = "VALIDATION_FAILED"

_WHOLE_NUMBER_TYPES = frozenset({"int_parsing", "int_type", "int_from_float"})


class FieldError(BaseModel):
    """Why one field was rejected. ``field`` is None when the whole request is at fault."""

    field: str | None
    message: str


class ValidationFailed(BaseModel):
    """Body of every 422 response."""

    detail: str = VALIDATION_FAILED
    errors: list[FieldError]


def _field_name(loc: Sequence[object]) -> str | None:
    # loc is ("body" | "query" | "path", name, ...); a bare ("body",) or a
    # trailing list index means no single named field is to blame.
    if len(loc) < 2 or not isinstance(loc[-1], str):
        return None
    return loc[-1]


def _message(error: Mapping[str, Any]) -> str:
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}
    if kind == "missing":
        return "Required."
    if kind == "string_too_short":
        minimum = ctx.get("min_length", 1)
        return "Required." if minimum == 1 else f"Must be at least {minimum} characters."
    if kind == "string_too_long":
        return f"Must be at most {ctx.get('max_length')} characters."
    if kind == "greater_than_equal":
        return f"Must be {ctx.get('ge')} or more."
    if kind == "greater_than":
        return f"Must be more than {ctx.get('gt')}."
    if kind == "less_than_equal":
        return f"Must be {ctx.get('le')} or less."
    if kind == "less_than":
        return f"Must be less than {ctx.get('lt')}."
    if kind in _WHOLE_NUMBER_TYPES:
        return "Must be a whole number."
    if kind == "uuid_parsing":
        return "Must be a valid ID."
    if kind == "enum":
        return f"Must be one of {ctx.get('expected')}."
    if kind == "extra_forbidden":
        return "Not an allowed field."
    if kind == "json_invalid":
        return "The request body is not valid JSON."
    # email-validator reports through pydantic's generic value_error.
    if kind == "value_error" and str(error.get("msg", "")).startswith(
        "value is not a valid email address"
    ):
        return "Enter a valid email address."
    return str(error.get("msg", "Invalid value."))


def field_errors(errors: Sequence[Mapping[str, Any]]) -> list[FieldError]:
    """User-facing messages for pydantic's raw validation errors.

    Only ``type``, ``loc``, ``ctx`` and ``msg`` are read; ``input`` is ignored so
    submitted values never reach the response.

    Example::

        field_errors([{"type": "missing", "loc": ("body", "title"), "msg": "Field required"}])
        # [FieldError(field="title", message="Required.")]
    """
    return [
        FieldError(field=_field_name(error.get("loc", ())), message=_message(error))
        for error in errors
    ]


def install_validation_handler(app: FastAPI) -> None:
    """Make every request-validation failure on ``app`` answer with ``ValidationFailed``.

    Example::

        app = FastAPI()
        install_validation_handler(app)
    """

    async def handle(_: Request, error: Exception) -> JSONResponse:
        if not isinstance(error, RequestValidationError):
            raise TypeError(f"expected RequestValidationError, got {type(error).__name__}")
        body = ValidationFailed(errors=field_errors(error.errors()))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=body.model_dump()
        )

    app.add_exception_handler(RequestValidationError, handle)
