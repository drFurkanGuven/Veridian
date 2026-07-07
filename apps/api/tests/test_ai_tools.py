import pytest

from veridian_api.domain.ai_tools import extract_ai_actions, strip_action_blocks


def test_extract_write_file_block() -> None:
    text = """Here is the fix:

```veridian-write-file
module top;
endmodule
```
"""
    actions = extract_ai_actions(text)
    assert len(actions) == 1
    assert actions[0]["action"] == "write_active_file"
    assert "module top;" in actions[0]["content"]


def test_strip_action_blocks_removes_tool_output() -> None:
    text = "Done.\n\n```veridian-write-file\nmodule tb;\nendmodule\n```\n"
    assert "veridian-write-file" not in strip_action_blocks(text)
    assert strip_action_blocks(text) == "Done."


def test_extract_write_file_with_path() -> None:
    text = """Creating testbench:

```veridian-write-file tb/tb_top.v
module tb_top;
endmodule
```
"""
    actions = extract_ai_actions(text)
    assert len(actions) == 1
    assert actions[0]["action"] == "write_file"
    assert actions[0]["path"] == "tb/tb_top.v"
    assert "module tb_top;" in actions[0]["content"]


def test_extract_create_file_block() -> None:
    text = """```veridian-create-file sim/tb.v
module tb;
endmodule
```"""
    actions = extract_ai_actions(text)
    assert len(actions) == 1
    assert actions[0]["action"] == "write_file"
    assert actions[0]["path"] == "sim/tb.v"

