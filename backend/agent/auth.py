from __future__ import annotations

import time
from typing import Any, Dict

from config import REQUIRE_AUTHORIZATION
from agent.errors import EditorError


READ_OPERATIONS = {"project.set_playhead"}


def authorize(operation: str, context: Dict[str, Any] | None) -> Dict[str, Any]:
    """Enforce permissions inside Viralist, independently of the MCP client."""
    context = context or {}
    if not context and not REQUIRE_AUTHORIZATION:
        return {"actorId": "local-unscoped", "allowedActions": ["*"]}
    if not context:
        raise EditorError("AUTH_CONTEXT_REQUIRED", "This Viralist runtime requires an authorization context.", recommended_action="Provide a manager-issued authorization context.", http_status=403)
    expires = context.get("expiresAt")
    if expires is not None and float(expires) < time.time():
        raise EditorError("AUTH_EXPIRED", "Authorization context has expired.", recommended_action="Request a fresh manager authorization.", http_status=403)
    allowed = set(context.get("allowedActions") or [])
    required = "control.kill_switch" if operation == "control.kill_switch" else "timeline.read" if operation in READ_OPERATIONS else "timeline.write"
    if "*" not in allowed and required not in allowed and operation not in allowed:
        raise EditorError("ACTION_FORBIDDEN", f"Authorization does not permit '{operation}'.", recommended_action="Request an authorization grant for this action.", details={"required": required}, http_status=403)
    return context
