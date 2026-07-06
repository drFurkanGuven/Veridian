from datetime import datetime
import enum
from typing import Optional
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import DateTime, String, TypeDecorator, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StrEnumType(TypeDecorator):
    """Persist str enums by value; accept legacy rows stored by member name."""

    impl = String
    cache_ok = True

    def __init__(self, enum_cls: type[enum.Enum], *, length: int = 64) -> None:
        super().__init__(length=length)
        self._enum_cls = enum_cls

    def process_bind_param(self, value: Optional[object], dialect) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, self._enum_cls):
            return value.value
        return str(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[enum.Enum]:
        if value is None:
            return None
        try:
            return self._enum_cls(value)
        except ValueError:
            pass
        try:
            return self._enum_cls[value]
        except KeyError:
            pass
        lowered = value.lower()
        try:
            return self._enum_cls(lowered)
        except ValueError as exc:
            raise LookupError(
                f"{value!r} is not a valid {self._enum_cls.__name__}"
            ) from exc


def str_enum(enum_cls: type[enum.Enum], name: Optional[str] = None) -> StrEnumType:
    """`name` kept for call-site clarity; columns are stored as plain strings."""
    _ = name
    return StrEnumType(enum_cls)


class UUIDPrimaryKeyMixin:
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
