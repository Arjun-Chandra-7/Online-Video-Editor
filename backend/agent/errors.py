from __future__ import annotations

from typing import Any, Dict, Optional


class EditorError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False, recommended_action: str = "", details: Optional[Dict[str, Any]] = None, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.recommended_action = recommended_action or "Inspect the project state and repair the request."
        self.details = details or {}
        self.http_status = http_status

    def payload(self) -> Dict[str, Any]:
        return {"success": False, "error": {"code": self.code, "message": self.message, "retryable": self.retryable, "recommendedAction": self.recommended_action, "details": self.details}}


def classify_exception(exc: Exception) -> EditorError:
    if isinstance(exc, EditorError):
        return exc
    text = str(exc)
    if "No space left" in text:
        return EditorError("DISK_FULL", "Insufficient disk space for this operation.", retryable=False, recommended_action="Free disk space and retry.", http_status=507)
    if "Permission" in text:
        return EditorError("PERMISSION_DENIED", "The operation was denied by the editor.", recommended_action="Request an authorization grant or use an approved path.", http_status=403)
    return EditorError("INTERNAL_ERROR", "The editor encountered an unexpected error.", retryable=False, recommended_action="Inspect the operation log and escalate with the operation ID.", details={"exception": text}, http_status=500)
