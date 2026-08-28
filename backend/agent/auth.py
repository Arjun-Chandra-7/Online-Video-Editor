from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional, Union

from config import MANAGER_SIGNING_KEY, REQUIRE_AUTHORIZATION, REQUIRE_SIGNED_TOKENS
from agent.errors import EditorError

READ_OPERATIONS = {"project.set_playhead", "timeline.inspect", "timeline.read", "project.inspect"}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("ascii"))


def create_signed_token(
    actor_id: str,
    allowed_actions: List[str],
    expires_in_seconds: int = 3600,
    project_id: Optional[str] = None,
    secret: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Issues a manager-signed authorization token for safe distributed agent execution."""
    key = (secret or MANAGER_SIGNING_KEY).encode("utf-8")
    now = time.time()
    exp = now + expires_in_seconds
    payload = {
        "iss": "viralyst-manager",
        "sub": actor_id,
        "actorId": actor_id,
        "allowedActions": allowed_actions,
        "projectId": project_id,
        "iat": round(now, 3),
        "exp": round(exp, 3),
        "expiresAt": round(exp, 3),
        "meta": metadata or {},
    }
    payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_raw)
    signature_base = f"v1.{payload_b64}".encode("utf-8")
    sig = hmac.new(key, signature_base, hashlib.sha256).hexdigest()
    return f"v1.{payload_b64}.{sig}"


def verify_signed_token(token: str, secret: Optional[str] = None) -> Dict[str, Any]:
    """Verifies a manager-signed token's cryptographic signature, expiration, and payload."""
    if not isinstance(token, str):
        raise EditorError("AUTH_TOKEN_INVALID", "Authorization token must be a string.", http_status=401)
    
    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()
    
    parts = clean_token.split(".")
    if len(parts) != 3 or parts[0] != "v1":
        raise EditorError("AUTH_TOKEN_MALFORMED", "Token format must be 'v1.<payload_b64>.<signature>'.", http_status=401)
    
    payload_b64, signature_hex = parts[1], parts[2]
    key = (secret or MANAGER_SIGNING_KEY).encode("utf-8")
    expected_sig = hmac.new(key, f"v1.{payload_b64}".encode("utf-8"), hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(signature_hex, expected_sig):
        raise EditorError(
            "AUTH_SIGNATURE_INVALID",
            "Token signature is invalid or has been tampered with.",
            recommended_action="Ensure the token is signed with the matching VIRALIST_SIGNING_KEY.",
            http_status=403,
        )
    
    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise EditorError("AUTH_PAYLOAD_INVALID", f"Token payload could not be decoded: {exc}", http_status=401) from exc
    
    exp = payload.get("exp") or payload.get("expiresAt")
    if exp is not None and float(exp) < time.time():
        raise EditorError(
            "AUTH_EXPIRED",
            "Manager-signed authorization token has expired.",
            recommended_action="Request a fresh manager authorization token.",
            details={"expiredAt": exp, "currentTime": time.time()},
            http_status=403,
        )
    
    return payload


def parse_authorization(context_or_token: Union[str, Dict[str, Any], None], secret: Optional[str] = None) -> Dict[str, Any]:
    """Parses and verifies either a signed token string, or a context dictionary."""
    if context_or_token is None:
        if not REQUIRE_AUTHORIZATION:
            return {"actorId": "local-unscoped", "allowedActions": ["*"]}
        raise EditorError(
            "AUTH_CONTEXT_REQUIRED",
            "This Viralist runtime requires an authorization token or context.",
            recommended_action="Provide a manager-issued signed token (VIRALIST_AUTHORIZATION_TOKEN or X-Viralist-Authorization).",
            http_status=403,
        )
    
    if isinstance(context_or_token, str):
        raw = context_or_token.strip()
        if raw.lower().startswith("bearer "):
            raw = raw[7:].strip()
        if raw.startswith("v1."):
            return verify_signed_token(raw, secret)
        if raw.startswith("{") and raw.endswith("}"):
            if REQUIRE_SIGNED_TOKENS:
                raise EditorError("AUTH_SIGNED_TOKEN_REQUIRED", "Plain JSON contexts are disabled; signed tokens are required.", http_status=403)
            try:
                data = json.loads(raw)
                return parse_authorization(data, secret)
            except json.JSONDecodeError as exc:
                raise EditorError("AUTH_CONTEXT_INVALID", f"Invalid JSON authorization header: {exc}", http_status=400) from exc
        # Attempt signed token verification
        return verify_signed_token(raw, secret)
    
    if isinstance(context_or_token, dict):
        if "token" in context_or_token and isinstance(context_or_token["token"], str):
            return verify_signed_token(context_or_token["token"], secret)
        if "signedToken" in context_or_token and isinstance(context_or_token["signedToken"], str):
            return verify_signed_token(context_or_token["signedToken"], secret)
        if REQUIRE_SIGNED_TOKENS:
            raise EditorError("AUTH_SIGNED_TOKEN_REQUIRED", "Unsigned authorization contexts are rejected by policy.", http_status=403)
        
        expires = context_or_token.get("expiresAt") or context_or_token.get("exp")
        if expires is not None and float(expires) < time.time():
            raise EditorError("AUTH_EXPIRED", "Authorization context has expired.", recommended_action="Request a fresh manager authorization.", http_status=403)
        return context_or_token
    
    raise EditorError("AUTH_CONTEXT_INVALID", f"Unsupported authorization context format: {type(context_or_token)}", http_status=400)


def authorize(
    operation: str,
    context: Union[str, Dict[str, Any], None],
    project_id: Optional[str] = None,
    secret: Optional[str] = None,
) -> Dict[str, Any]:
    """Enforce permissions inside Viralist, verifying Manager signature and scoped permissions."""
    ctx = parse_authorization(context, secret)
    
    # Project ID scoping check
    token_proj = ctx.get("projectId")
    if token_proj and project_id and token_proj != project_id:
        raise EditorError(
            "PROJECT_FORBIDDEN",
            f"Authorization token is scoped to project '{token_proj}', cannot operate on '{project_id}'.",
            http_status=403,
        )
    
    allowed = set(ctx.get("allowedActions") or [])
    if "*" in allowed:
        return ctx
    
    required = (
        "control.kill_switch"
        if operation in {"control.kill_switch", "kill_switch"}
        else "project.export"
        if operation in {"project.export", "export", "job.export"}
        else "timeline.read"
        if operation in READ_OPERATIONS
        else "timeline.write"
    )
    
    if required not in allowed and operation not in allowed:
        raise EditorError(
            "ACTION_FORBIDDEN",
            f"Authorization does not permit '{operation}'.",
            recommended_action=f"Request an authorization grant for '{required}' or '{operation}'.",
            details={"required": required, "allowed": list(allowed), "operation": operation},
            http_status=403,
        )
    
    return ctx
