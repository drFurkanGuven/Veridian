from __future__ import annotations

import pytest

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import UnauthorizedError
from veridian_api.domain.enums import OAuthProvider
from veridian_api.infrastructure.auth.oauth import build_authorization_url
from veridian_api.infrastructure.auth.password import hash_password, verify_password
from veridian_api.infrastructure.auth.tokens import (
    create_access_token,
    create_oauth_state,
    create_refresh_token,
    decode_access_token,
    hash_token,
    verify_oauth_state,
)
from uuid import uuid4


def test_hash_password_roundtrip() -> None:
    hashed = hash_password("secure-password-123")
    assert verify_password("secure-password-123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip() -> None:
    settings = Settings(jwt_secret="test-secret-key-for-jwt-signing")
    user_id = uuid4()
    token, expires_in = create_access_token(user_id, settings)
    assert expires_in == settings.jwt_access_token_expire_minutes * 60
    assert decode_access_token(token, settings) == user_id


def test_refresh_token_hash_is_stable() -> None:
    token = create_refresh_token()
    assert hash_token(token) == hash_token(token)
    assert len(hash_token(token)) == 64


def test_oauth_state_roundtrip() -> None:
    settings = Settings(jwt_secret="test-secret-key-for-jwt-signing")
    state = create_oauth_state(OAuthProvider.GOOGLE.value, settings)
    verify_oauth_state(state, OAuthProvider.GOOGLE.value, settings)


def test_oauth_state_rejects_wrong_provider() -> None:
    settings = Settings(jwt_secret="test-secret-key-for-jwt-signing")
    state = create_oauth_state(OAuthProvider.GOOGLE.value, settings)
    with pytest.raises(UnauthorizedError):
        verify_oauth_state(state, OAuthProvider.GITHUB.value, settings)


def test_google_authorization_url() -> None:
    settings = Settings(
        google_client_id="google-client-id",
        google_redirect_uri="http://localhost:8000/callback",
    )
    url = build_authorization_url(OAuthProvider.GOOGLE, "state-123", settings)
    assert "accounts.google.com" in url
    assert "google-client-id" in url
    assert "state-123" in url


def test_github_authorization_url() -> None:
    settings = Settings(
        github_client_id="github-client-id",
        github_redirect_uri="http://localhost:8000/callback",
    )
    url = build_authorization_url(OAuthProvider.GITHUB, "state-456", settings)
    assert "github.com/login/oauth/authorize" in url
    assert "github-client-id" in url
