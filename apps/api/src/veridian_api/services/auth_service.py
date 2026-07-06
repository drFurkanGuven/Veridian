from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import ConflictError, UnauthorizedError, ValidationError
from veridian_api.domain.enums import OAuthProvider
from veridian_api.infrastructure.auth.oauth import (
    OAuthUserInfo,
    build_authorization_url,
    exchange_code_for_user,
)
from veridian_api.infrastructure.auth.password import hash_password, verify_password
from veridian_api.infrastructure.auth.tokens import (
    create_access_token,
    create_oauth_state,
    create_refresh_token,
    decode_access_token,
    hash_token,
    refresh_token_expires_at,
    verify_oauth_state,
)
from veridian_api.infrastructure.database.models.oauth import OAuthAccount, UserSession
from veridian_api.infrastructure.database.models.user import User


@dataclass(frozen=True)
class AuthResult:
    user: User
    access_token: str
    refresh_token: str
    expires_in: int


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings

    async def register(
        self,
        email: str,
        password: str,
        display_name: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuthResult:
        existing = await self._db.scalar(select(User.id).where(User.email == email.lower()))
        if existing:
            raise ConflictError("Email already registered")

        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            display_name=display_name.strip(),
            email_verified=False,
        )
        self._db.add(user)
        await self._db.flush()
        return await self._issue_tokens(user, user_agent=user_agent, ip_address=ip_address)

    async def login(
        self,
        email: str,
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuthResult:
        user = await self._db.scalar(select(User).where(User.email == email.lower()))
        if user is None or not user.password_hash:
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        return await self._issue_tokens(user, user_agent=user_agent, ip_address=ip_address)

    async def refresh(
        self,
        refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuthResult:
        token_hash = hash_token(refresh_token)
        now = datetime.now(timezone.utc)

        session = await self._db.scalar(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
        )
        if session is None:
            raise UnauthorizedError("Invalid or expired refresh token")

        session.revoked_at = now
        return await self._issue_tokens(
            session.user,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def logout(self, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        session = await self._db.scalar(
            select(UserSession).where(
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
        )
        if session is not None:
            session.revoked_at = datetime.now(timezone.utc)

    async def get_user_by_id(self, user_id: UUID) -> User:
        user = await self._db.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise UnauthorizedError("User not found")
        return user

    def get_authorization_url(self, provider: OAuthProvider) -> tuple[str, str]:
        state = create_oauth_state(provider.value, self._settings)
        url = build_authorization_url(provider, state, self._settings)
        return url, state

    async def oauth_callback(
        self,
        provider: OAuthProvider,
        code: str,
        state: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuthResult:
        verify_oauth_state(state, provider.value, self._settings)
        oauth_user = await exchange_code_for_user(provider, code, self._settings)
        user = await self._upsert_oauth_user(provider, oauth_user)
        return await self._issue_tokens(user, user_agent=user_agent, ip_address=ip_address)

    async def _upsert_oauth_user(self, provider: OAuthProvider, info: OAuthUserInfo) -> User:
        account = await self._db.scalar(
            select(OAuthAccount)
            .options(selectinload(OAuthAccount.user))
            .where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == info.provider_user_id,
            )
        )
        if account is not None:
            account.user.display_name = info.display_name
            account.user.avatar_url = info.avatar_url
            if info.email_verified:
                account.user.email_verified = True
            return account.user

        user = await self._db.scalar(select(User).where(User.email == info.email.lower()))
        if user is None:
            user = User(
                email=info.email.lower(),
                password_hash=None,
                display_name=info.display_name,
                avatar_url=info.avatar_url,
                email_verified=info.email_verified,
            )
            self._db.add(user)
            await self._db.flush()
        else:
            user.display_name = info.display_name
            user.avatar_url = info.avatar_url
            if info.email_verified:
                user.email_verified = True

        self._db.add(
            OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=info.provider_user_id,
            )
        )
        await self._db.flush()
        return user

    async def _issue_tokens(
        self,
        user: User,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuthResult:
        access_token, expires_in = create_access_token(user.id, self._settings)
        refresh_token = create_refresh_token()

        self._db.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                user_agent=user_agent,
                ip_address=ip_address,
                expires_at=refresh_token_expires_at(self._settings),
            )
        )
        await self._db.flush()

        return AuthResult(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    @staticmethod
    def decode_access_token(token: str, settings: Settings) -> UUID:
        return decode_access_token(token, settings)
