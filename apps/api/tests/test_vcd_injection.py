from pathlib import Path

from veridian_api.domain.vcd_injection import ensure_vcd_dump, find_vcd_output, infer_module_name


def test_infer_module_name() -> None:
    source = "module tb_top;\nendmodule\n"
    assert infer_module_name(source, "top") == "tb_top"


def test_ensure_vcd_dump_skips_existing() -> None:
    source = 'module tb;\ninitial $dumpfile("x.vcd");\nendmodule\n'
    updated, injected = ensure_vcd_dump(source, "tb")
    assert injected is False
    assert updated == source


def test_ensure_vcd_dump_injects_before_endmodule() -> None:
    source = "module tb;\n  initial #1 $finish;\nendmodule\n"
    updated, injected = ensure_vcd_dump(source, "tb")
    assert injected is True
    assert '$dumpfile("dump.vcd")' in updated
    assert "$dumpvars(0, tb)" in updated
    assert updated.index("$dumpfile") < updated.lower().index("endmodule")


def test_find_vcd_output_prefers_dump_vcd(tmp_path: Path) -> None:
    (tmp_path / "other.vcd").write_text("x", encoding="utf-8")
    dump = tmp_path / "dump.vcd"
    dump.write_text("longer-content", encoding="utf-8")
    assert find_vcd_output(tmp_path) == dump
