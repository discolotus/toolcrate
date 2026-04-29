"""Domain exceptions used across services and converted to RFC 7807 in web layer."""

from __future__ import annotations


class ToolcrateError(Exception):
    code: str = "toolcrate.error"


class NotFound(ToolcrateError):
    code = "not_found"


class Conflict(ToolcrateError):
    code = "conflict"


class ValidationError(ToolcrateError):
    code = "validation_error"


class IntegrationError(ToolcrateError):
    code = "integration_error"
