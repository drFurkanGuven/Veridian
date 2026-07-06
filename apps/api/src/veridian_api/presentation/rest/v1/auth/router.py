from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request

from veridian_api.core.config import Settings
from veridian_api.core.deps import get_current_user, get_db, get_settings_dep
from veridian_api.domain.enums import OAuthProvider
from veridian_api.infrastructure.database.models.user import User
from veridian_api.presentation.rest.v1.auth.schemas import (
    AuthResponse,
    AuthTokensResponse,
    LoginRequest,
    LogoutRequest,
    OAuthCallbackRequest,
    OAuthProvidersResponse,
    OAuthUrlResponse,
    RefreshTokenRequest,
    RegisterRequest,
    UserResponse,
    user_to_response,
)
from veridian_api.services.auth_service import AuthResult, AuthService

router = APIRouter()


def _client_meta(request: Request) -> tuple[Optional[str], Optional[str]]:
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None
    return user_agent, client_host


def _auth_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        user=user_to_response(result.user),
        tokens=AuthTokensResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            expires_in=result.expires_in,
        ),
    )


def get_auth_service(
    db=Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> AuthService:
    return AuthService(db, settings)


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    user_agent, ip_address = _client_meta(request)
    result = await auth.register(
        email=str(body.email),
        password=body.password,
        display_name=body.display_name,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return _auth_response(result)


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    user_agent, ip_address = _client_meta(request)
    result = await auth.login(
        email=str(body.email),
        password=body.password,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return _auth_response(result)


@router.post("/refresh", response_model=AuthTokensResponse)
async def refresh(
    body: RefreshTokenRequest,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> AuthTokensResponse:
    user_agent, ip_address = _client_meta(request)
    result = await auth.refresh(
        refresh_token=body.refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return AuthTokensResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
    )


@router.post("/logout", status_code=204)
async def logout(
    body: LogoutRequest,
    auth: AuthService = Depends(get_auth_service),
) -> None:
    await auth.logout(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return user_to_response(current_user)


@router.get("/providers", response_model=OAuthProvidersResponse)
async def auth_providers(settings: Settings = Depends(get_settings_dep)) -> OAuthProvidersResponse:
    google_ok = bool(settings.google_client_id and settings.google_client_secret)
    github_ok = bool(settings.github_client_id and settings.github_client_secret)
    return OAuthProvidersResponse(
        google=google_ok,
        github=github_ok,
        google_redirect_uri=settings.google_oauth_redirect_uri if google_ok else None,
        github_redirect_uri=settings.github_oauth_redirect_uri if github_ok else None,
    )


@router.get("/google/url", response_model=OAuthUrlResponse)
async def google_auth_url(auth: AuthService = Depends(get_auth_service)) -> OAuthUrlResponse:
    url, state = auth.get_authorization_url(OAuthProvider.GOOGLE)
    return OAuthUrlResponse(url=url, state=state)


@router.post("/google/callback", response_model=AuthResponse)
async def google_callback(
    body: OAuthCallbackRequest,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    user_agent, ip_address = _client_meta(request)
    result = await auth.oauth_callback(
        OAuthProvider.GOOGLE,
        body.code,
        body.state,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return _auth_response(result)


@router.get("/github/url", response_model=OAuthUrlResponse)
async def github_auth_url(auth: AuthService = Depends(get_auth_service)) -> OAuthUrlResponse:
    url, state = auth.get_authorization_url(OAuthProvider.GITHUB)
    return OAuthUrlResponse(url=url, state=state)


@router.post("/github/callback", response_model=AuthResponse)
async def github_callback(
    body: OAuthCallbackRequest,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    user_agent, ip_address = _client_meta(request)
    result = await auth.oauth_callback(
        OAuthProvider.GITHUB,
        body.code,
        body.state,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return _auth_response(result)
