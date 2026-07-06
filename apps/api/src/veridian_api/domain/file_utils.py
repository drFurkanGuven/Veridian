from __future__ import annotations

from typing import Optional
from uuid import UUID

from veridian_api.domain.enums import HdlLanguage


def detect_language(filename: str) -> HdlLanguage:
    lower = filename.lower()
    if lower.endswith(".sv") or lower.endswith(".svh"):
        return HdlLanguage.SYSTEMVERILOG
    if lower.endswith(".vhd") or lower.endswith(".vhdl"):
        return HdlLanguage.VHDL
    if lower.endswith(".xdc"):
        return HdlLanguage.XDC
    if lower.endswith(".qsf"):
        return HdlLanguage.QSF
    return HdlLanguage.VERILOG
