import pytest

from veridian_api.domain.file_utils import detect_language
from veridian_api.domain.enums import HdlLanguage
from veridian_api.infrastructure.storage.object_storage import join_path, sha256_hex


def test_detect_language_verilog() -> None:
    assert detect_language("top.v") == HdlLanguage.VERILOG


def test_detect_language_systemverilog() -> None:
    assert detect_language("top.sv") == HdlLanguage.SYSTEMVERILOG


def test_join_path_root() -> None:
    assert join_path(None, "src") == "/src"


def test_join_path_nested() -> None:
    assert join_path("/src", "top.v") == "/src/top.v"


def test_sha256_hex() -> None:
    assert len(sha256_hex(b"module top; endmodule")) == 64
