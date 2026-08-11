"""Minimal Supabase email/password auth client for Streamlit."""

from __future__ import annotations

import os
import time
from typing import Any

import requests


class SupabaseAuthError(RuntimeError):
    pass


def validate_signup(
    email: str,
    password: str,
    privacy_accepted: bool,
) -> str | None:
    """Return a user-facing signup validation error, if any."""
    if not email.strip():
        return "Enter your email address."
    if not privacy_accepted:
        return "Accept the privacy notice before creating an account."
    if len(password) < 8:
        return "Use a password with at least 8 characters."
    return None


def friendly_sign_in_error(error: SupabaseAuthError) -> str:
    """Make Supabase's credential error actionable without leaking account state."""
    message = str(error)
    if "invalid login credentials" in message.lower():
        return (
            "No account matches those credentials, or the password is incorrect. "
            "If this is your first visit, use the Create account tab above."
        )
    return message


def is_configured() -> bool:
    return bool(
        os.getenv("SUPABASE_URL", "").strip()
        and os.getenv("SUPABASE_ANON_KEY", "").strip()
    )


def sign_in(email: str, password: str) -> dict[str, Any]:
    payload = _request(
        "POST",
        "/auth/v1/token?grant_type=password",
        json={"email": email, "password": password},
    )
    return _session(payload)


def sign_up(email: str, password: str) -> dict[str, Any] | None:
    payload = _request(
        "POST",
        "/auth/v1/signup",
        json={"email": email, "password": password},
    )
    return _session(payload) if payload.get("access_token") else None


def refresh_session(refresh_token: str) -> dict[str, Any]:
    payload = _request(
        "POST",
        "/auth/v1/token?grant_type=refresh_token",
        json={"refresh_token": refresh_token},
    )
    return _session(payload)


def sign_out(access_token: str) -> None:
    _request("POST", "/auth/v1/logout", access_token=access_token)


def claim_analysis_slot(access_token: str) -> bool:
    return bool(
        _request(
            "POST",
            "/rest/v1/rpc/claim_analysis_slot",
            access_token=access_token,
            json={},
        )
    )


def claim_chat_slot(access_token: str) -> bool:
    return bool(
        _request(
            "POST",
            "/rest/v1/rpc/claim_chat_slot",
            access_token=access_token,
            json={},
        )
    )


def _session(payload: dict[str, Any]) -> dict[str, Any]:
    payload["expires_at"] = time.time() + int(payload.get("expires_in", 3600))
    return payload


def _request(
    method: str,
    path: str,
    access_token: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    base_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not base_url or not anon_key:
        raise SupabaseAuthError("Supabase authentication is not configured.")

    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {access_token or anon_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.request(
            method,
            f"{base_url}{path}",
            headers=headers,
            timeout=20,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise SupabaseAuthError(
            f"Authentication service is unavailable: {exc}"
        ) from exc

    if not response.ok:
        try:
            body = response.json()
            detail = (
                body.get("msg") or body.get("message") or body.get("error_description")
            )
        except ValueError:
            detail = response.text
        raise SupabaseAuthError(
            detail or f"Authentication failed ({response.status_code})."
        )
    return response.json() if response.content else {}
