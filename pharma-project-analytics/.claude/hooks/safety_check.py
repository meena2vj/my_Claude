#!/usr/bin/env python3
"""PreToolUse safety hook for Pharma Project Analytics.

Blocks destructive deletion, access to secrets/.env files, commands that
try to expose credentials, and commands operating outside the project
directory. Reads a JSON hook payload on stdin; exits 2 (block) with a
reason on stderr, or 0 (allow).
"""
import json
import os
import re
import shlex
import sys

DESTRUCTIVE_PATTERNS = [
    r"\brm\s+.*-[a-zA-Z]*r[a-zA-Z]*f\b",   # rm -rf, rm -fr, rm -Rf ...
    r"\brm\s+.*-[a-zA-Z]*f[a-zA-Z]*r\b",
    r"\bfind\b.*-delete\b",
    r"\bgit\s+clean\s+.*-[a-zA-Z]*f",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+push\s+.*--force\b",
    r"\bgit\s+branch\s+-D\b",
    r"\bdd\s+if=",
    r"\bmkfs\b",
    r"\b:\(\)\{.*:\|:.*\}",  # fork bomb style
    r"\btruncate\b.*-s\s*0",
    r">\s*/dev/sd",
]

SECRET_FILENAME_PATTERN = re.compile(
    r"(^|/|\\)(\.env(\..*)?|.*\.pem|.*\.key|id_rsa.*|.*secret.*|.*credentials.*"
    r"|\.aws/credentials|\.npmrc|\.git-credentials)$",
    re.IGNORECASE,
)

CREDENTIAL_EXPOSURE_PATTERNS = [
    r"\bcat\s+.*(\.env|secret|credential|\.pem|\.key|id_rsa)",
    r"\bprintenv\b",
    r"\benv\b\s*$",
    r"\becho\s+\$[a-z_]*(key|token|secret|password|cred)",
    r"\bexport\b.*(key|token|secret|password)=.*\|.*curl",
    r"\bcurl\b.*(\.env|secret|credential)",
    r"\bcat\s+~/\.aws/credentials",
]

FILE_TARGETING_TOOLS = {"Read", "Write", "Edit", "NotebookEdit", "Glob", "Grep"}


def deny(reason: str) -> None:
    sys.stderr.write(f"safety_check: blocked - {reason}\n")
    sys.exit(2)


def allow() -> None:
    sys.exit(0)


def project_root() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())


def is_outside_project(path: str, root: str) -> bool:
    if not path:
        return False
    abs_path = os.path.abspath(os.path.join(root, path))
    abs_root = os.path.abspath(root)
    return os.path.commonpath([abs_path, abs_root]) != abs_root


def shell_tokens(command: str) -> list:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def check_bash_command(command: str, root: str) -> None:
    lowered = command.lower()

    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, lowered):
            deny(f"destructive command pattern matched: {pattern}")

    for pattern in CREDENTIAL_EXPOSURE_PATTERNS:
        if re.search(pattern, lowered):
            deny(f"command appears to expose credentials: {pattern}")

    if SECRET_FILENAME_PATTERN.search(command):
        deny("command references a secret/.env file")

    # shlex-aware check for absolute paths outside the project root - handles
    # quoted paths (and paths containing spaces) correctly, unlike naive
    # whitespace splitting.
    tokens = shell_tokens(command)

    for token in tokens:
        if not token.startswith("/") or token.startswith(("/tmp", "/dev/null")):
            continue
        if is_outside_project(token, root):
            deny(f"command references a path outside the project directory: {token}")

    for i, token in enumerate(tokens):
        if token == "cd" and i + 1 < len(tokens):
            target = tokens[i + 1]
            if target.startswith("/") and not target.startswith(("/tmp", "/dev/null")):
                if is_outside_project(target, root):
                    deny(f"command changes directory outside the project: {target}")


def check_file_path(path: str, root: str) -> None:
    if not path:
        return
    if SECRET_FILENAME_PATTERN.search(path):
        deny(f"access to secret/.env file blocked: {path}")
    if is_outside_project(path, root):
        deny(f"file path outside the project directory: {path}")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        allow()
        return

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    root = project_root()

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            check_bash_command(command, root)

    if tool_name in FILE_TARGETING_TOOLS:
        for key in ("file_path", "path", "notebook_path", "pattern"):
            value = tool_input.get(key)
            if isinstance(value, str) and key != "pattern":
                check_file_path(value, root)

    allow()


if __name__ == "__main__":
    main()
