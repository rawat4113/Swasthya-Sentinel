"""Password hashing and signed bearer-token helpers for the local MVP.

This is suitable for a controlled hackathon/demo deployment. Production deployments
should use a managed identity provider, HTTPS, secret rotation and hardened session
management.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

FORBIDDEN_IDENTIFIERS = {
    'patient_id', 'patient_name', 'employee_id', 'employee_name', 'phone',
    'phone_number', 'email', 'national_id', 'aadhaar', 'medical_record_number'
}


def reject_personal_identifiers(field_names):
    present = FORBIDDEN_IDENTIFIERS.intersection(
        {str(x).strip().lower().replace(' ', '_') for x in field_names}
    )
    if present:
        raise ValueError('Personal identifiers are not accepted; aggregate the observations first.')


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError('Password must contain at least 10 characters.')
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 310_000)
    return f"pbkdf2_sha256$310000${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(derived).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_b64, digest_b64 = stored.split('$', 3)
        if algorithm != 'pbkdf2_sha256':
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, binascii.Error):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def issue_access_token(username: str, role: str, secret: str, expires_seconds: int = 8 * 60 * 60) -> str:
    payload = {'sub': username, 'role': role, 'exp': int(time.time()) + expires_seconds}
    body = _b64(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode())
    signature = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f'{body}.{signature}'


def decode_access_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        body, supplied_signature = token.split('.', 1)
        expected_signature = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None
        payload = json.loads(_unb64(body))
        if int(payload.get('exp', 0)) < int(time.time()):
            return None
        if not payload.get('sub') or not payload.get('role'):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, binascii.Error):
        return None
