from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError, ValidationError
from veridian_api.domain.enums import AuditEventType, OAuthProvider, UserRole
from veridian_api.infrastructure.auth.oauth import (
    OAuthUserInfo,
    build_authorization_url,
    exchange_code_for_user,
)
from veridian_api.infrastructure.auth.password import hash_password, verify_password
from veridian_api.infrastructure.auth.password_policy import validate_password
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
from veridian_api.services.audit_service import AuditService


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
        self._audit = AuditService(db)

    async def register(
        self,
        email: str,
        password: str,
        display_name: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuthResult:
        normalized_email = email.lower()
        existing = await self._db.scalar(select(User.id).where(User.email == normalized_email))
        if existing:
            raise ConflictError("Email already registered")

        validate_password(password, min_length=self._settings.auth_min_password_length)

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            display_name=display_name.strip(),
            email_verified=False,
        )
        self._maybe_promote_admin(user)
        self._db.add(user)
        await self._db.flush()
        await self._audit.record(
            AuditEventType.REGISTER,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return await self._issue_tokens(user, user_agent=user_agent, ip_address=ip_address)

    async def login(
        self,
        email: str,
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuthResult:
        normalized_email = email.lower()
        user = await self._db.scalar(select(User).where(User.email == normalized_email))
        if user is None or not user.password_hash:
            await self._audit.record(
                AuditEventType.LOGIN_FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"email": normalized_email, "reason": "invalid_credentials"},
            )
            raise UnauthorizedError("Invalid email or password")

        self._ensure_account_active(user)
        self._ensure_not_locked(user)

        if not verify_password(password, user.password_hash):
            await self._record_failed_login(user, ip_address=ip_address, user_agent=user_agent)
            raise UnauthorizedError("Invalid email or password")

        await self._record_successful_login(user, ip_address=ip_address, user_agent=user_agent)
        self._maybe_promote_admin(user)
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

        self._ensure_account_active(session.user)
        self._ensure_not_locked(session.user)

        session.revoked_at = now
        return await self._issue_tokens(
            session.user,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def logout(
        self,
        refresh_token: str,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        token_hash = hash_token(refresh_token)
        session = await self._db.scalar(
            select(UserSession).where(
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
        )
        if session is not None:
            session.revoked_at = datetime.now(timezone.utc)
            await self._audit.record(
                AuditEventType.LOGOUT,
                user_id=session.user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

    async def get_user_by_id(self, user_id: UUID) -> User:
        user = await self._db.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise UnauthorizedError("User not found")
        self._ensure_account_active(user)
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
        self._ensure_account_active(user)
        self._maybe_promote_admin(user)
        await self._record_successful_login(user, ip_address=ip_address, user_agent=user_agent)
        await self._audit.record(
            AuditEventType.OAUTH_LOGIN,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"provider": provider.value},
        )
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
            self._maybe_promote_admin(user)
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
        self._ensure_account_active(user)

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

    def _maybe_promote_admin(self, user: User) -> None:
        if user.email.lower() in self._settings.admin_email_list:
            user.role = UserRole.ADMIN

    def _ensure_account_active(self, user: User) -> None:
        if not user.is_active:
            raise ForbiddenError("Account is disabled")

    def _ensure_not_locked(self, user: User) -> None:
        now = datetime.now(timezone.utc)
        if user.locked_until is not None and user.locked_until > now:
            raise ForbiddenError("Account is temporarily locked due to failed login attempts")

    async def _record_failed_login(
        self,
        user: User,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        user.failed_login_attempts += 1
        locked = False
        if user.failed_login_attempts >= self._settings.auth_max_login_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=self._settings.auth_lockout_minutes
            )
            locked = True
            await self._audit.record(
                AuditEventType.ACCOUNT_LOCKED,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"attempts": user.failed_login_attempts},
            )
        await self._audit.record(
            AuditEventType.LOGIN_FAILED,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"attempts": user.failed_login_attempts, "locked": locked},
        )

    async def _record_successful_login(
        self,
        user: User,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        await self._audit.record(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def decode_access_token(token: str, settings: Settings) -> UUID:
        return decode_access_token(token, settings)
