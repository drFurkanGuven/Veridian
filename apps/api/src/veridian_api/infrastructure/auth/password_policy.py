from __future__ import annotations

import re

from veridian_api.core.exceptions import ValidationError

_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


def validate_password(password: str, min_length: int = 8) -> None:
    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters")
    if not _HAS_LETTER.search(password):
        raise ValidationError("Password must contain at least one letter")
    if not _HAS_DIGIT.search(password):
        raise ValidationError("Password must contain at least one digit")
