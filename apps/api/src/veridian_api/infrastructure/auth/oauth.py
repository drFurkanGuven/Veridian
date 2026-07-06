from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from typing import Any
from urllib.parse import urlencode

import httpx

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import UnauthorizedError, ValidationError
from veridian_api.domain.enums import OAuthProvider


@dataclass(frozen=True)
class OAuthUserInfo:
    provider_user_id: str
    email: str
    display_name: str
    avatar_url: Optional[str]
    email_verified: bool


def build_authorization_url(provider: OAuthProvider, state: str, settings: Settings) -> str:
    if provider == OAuthProvider.GOOGLE:
        if not settings.google_client_id:
            raise ValidationError("Google OAuth is not configured")
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    if provider == OAuthProvider.GITHUB:
        if not settings.github_client_id:
            raise ValidationError("GitHub OAuth is not configured")
        params = {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_oauth_redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    raise ValidationError(f"Unsupported OAuth provider: {provider}")


async def exchange_code_for_user(
    provider: OAuthProvider,
    code: str,
    settings: Settings,
) -> OAuthUserInfo:
    async with httpx.AsyncClient(timeout=15.0) as client:
        if provider == OAuthProvider.GOOGLE:
            return await _google_user_info(client, code, settings)
        if provider == OAuthProvider.GITHUB:
            return await _github_user_info(client, code, settings)
    raise ValidationError(f"Unsupported OAuth provider: {provider}")


async def _google_user_info(
    client: httpx.AsyncClient,
    code: str,
    settings: Settings,
) -> OAuthUserInfo:
    if not settings.google_client_id or not settings.google_client_secret:
        raise ValidationError("Google OAuth is not configured")

    token_response = await client.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    if token_response.status_code != 200:
        raise UnauthorizedError("Google token exchange failed")

    access_token = token_response.json().get("access_token")
    if not access_token:
        raise UnauthorizedError("Google token exchange failed")

    profile_response = await client.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if profile_response.status_code != 200:
        raise UnauthorizedError("Failed to fetch Google profile")

    profile: dict[str, Any] = profile_response.json()
    email = profile.get("email")
    if not email:
        raise UnauthorizedError("Google account has no email")

    return OAuthUserInfo(
        provider_user_id=str(profile.get("sub", "")),
        email=str(email),
        display_name=str(profile.get("name") or email.split("@")[0]),
        avatar_url=profile.get("picture"),
        email_verified=bool(profile.get("email_verified", False)),
    )


async def _github_user_info(
    client: httpx.AsyncClient,
    code: str,
    settings: Settings,
) -> OAuthUserInfo:
    if not settings.github_client_id or not settings.github_client_secret:
        raise ValidationError("GitHub OAuth is not configured")

    token_response = await client.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": settings.github_oauth_redirect_uri,
        },
    )
    if token_response.status_code != 200:
        raise UnauthorizedError("GitHub token exchange failed")

    access_token = token_response.json().get("access_token")
    if not access_token:
        raise UnauthorizedError("GitHub token exchange failed")

    profile_response = await client.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
    )
    if profile_response.status_code != 200:
        raise UnauthorizedError("Failed to fetch GitHub profile")

    profile: dict[str, Any] = profile_response.json()
    emails_response = await client.get(
        "https://api.github.com/user/emails",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
    )
    email = _pick_github_email(emails_response.json() if emails_response.status_code == 200 else [])
    if not email:
        raise UnauthorizedError("GitHub account has no public email")

    return OAuthUserInfo(
        provider_user_id=str(profile.get("id", "")),
        email=email,
        display_name=str(profile.get("name") or profile.get("login") or email.split("@")[0]),
        avatar_url=profile.get("avatar_url"),
        email_verified=True,
    )


def _pick_github_email(emails: list[dict[str, Any]]) -> Optional[str]:
    primary_verified = next(
        (item["email"] for item in emails if item.get("primary") and item.get("verified")),
        None,
    )
    if primary_verified:
        return str(primary_verified)

    verified = next((item["email"] for item in emails if item.get("verified")), None)
    if verified:
        return str(verified)

    if emails:
        return str(emails[0].get("email", ""))

    return None
