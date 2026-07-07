from __future__ import annotations

import json
import re
from typing import Any

WRITE_FILE_BLOCK = re.compile(r"```veridian-write-file\n([\s\S]*?)```", re.MULTILINE)
WRITE_PATH_FILE_BLOCK = re.compile(
    r"```veridian-write-file ([^\n]+)\n([\s\S]*?)```",
    re.MULTILINE,
)
CREATE_FILE_BLOCK = re.compile(
    r"```veridian-create-file ([^\n]+)\n([\s\S]*?)```",
    re.MULTILINE,
)
ACTION_BLOCK = re.compile(r"```veridian-action\n([\s\S]*?)```", re.MULTILINE)


def extract_ai_actions(text: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    for match in WRITE_PATH_FILE_BLOCK.finditer(text):
        path = match.group(1).strip()
        content = match.group(2).rstrip("\n")
        if path and content:
            actions.append({"action": "write_file", "path": path, "content": content})

    for match in CREATE_FILE_BLOCK.finditer(text):
        path = match.group(1).strip()
        content = match.group(2).rstrip("\n")
        if path and content:
            actions.append({"action": "write_file", "path": path, "content": content})

    for match in WRITE_FILE_BLOCK.finditer(text):
        content = match.group(1).rstrip("\n")
        if content:
            actions.append({"action": "write_active_file", "content": content})

    for match in ACTION_BLOCK.finditer(text):
        raw = match.group(1).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        action = payload.get("action")
        if action == "write_active_file":
            content = payload.get("content")
            if isinstance(content, str) and content.strip():
                actions.append({"action": "write_active_file", "content": content})
        elif action in {"write_file", "create_file"}:
            path = payload.get("path")
            content = payload.get("content")
            if isinstance(path, str) and path.strip() and isinstance(content, str) and content.strip():
                actions.append({"action": "write_file", "path": path.strip(), "content": content})

    return actions


def strip_action_blocks(text: str) -> str:
    cleaned = WRITE_PATH_FILE_BLOCK.sub("", text)
    cleaned = CREATE_FILE_BLOCK.sub("", cleaned)
    cleaned = WRITE_FILE_BLOCK.sub("", cleaned)
    cleaned = ACTION_BLOCK.sub("", cleaned)
    return cleaned.strip()
