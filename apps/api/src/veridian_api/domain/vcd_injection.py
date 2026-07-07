from __future__ import annotations

import re
from pathlib import Path

_MODULE_RE = re.compile(r"^\s*module\s+(\w+)", re.MULTILINE)


def infer_module_name(source: str, fallback: str) -> str:
    match = _MODULE_RE.search(source)
    return match.group(1) if match else fallback


def ensure_vcd_dump(source: str, module_name: str, dump_file: str = "dump.vcd") -> tuple[str, bool]:
    if "$dumpfile" in source.lower():
        return source, False

    block = f"""
  // Veridian: auto waveform capture
  initial begin
    $dumpfile("{dump_file}");
    $dumpvars(0, {module_name});
  end
"""
    lowered = source.lower()
    endmodule_index = lowered.rfind("endmodule")
    if endmodule_index == -1:
        return source.rstrip() + "\n" + block, True

    return source[:endmodule_index] + block + source[endmodule_index:], True


def find_vcd_output(work_dir: Path, preferred_name: str = "dump.vcd") -> Path | None:
    preferred = work_dir / preferred_name
    if preferred.exists() and preferred.stat().st_size > 0:
        return preferred

    candidates = [path for path in work_dir.glob("*.vcd") if path.is_file() and path.stat().st_size > 0]
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_size)
