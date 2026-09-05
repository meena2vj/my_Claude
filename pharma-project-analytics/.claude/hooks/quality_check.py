#!/usr/bin/env python3
"""PostToolUse quality hook for Pharma Project Analytics.

After a Write/Edit on a .py file, run a fast, non-blocking syntax check
(py_compile only - no test runs, no servers, no long-running processes).
Reports problems to Claude via stderr/exit code 2; otherwise exits 0.
"""
import json
import py_compile
import sys
import tempfile


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "")

    if not file_path or not file_path.endswith(".py"):
        sys.exit(0)

    try:
        with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as cfile:
            py_compile.compile(file_path, cfile=cfile.name, doraise=True)
    except FileNotFoundError:
        sys.exit(0)
    except py_compile.PyCompileError as exc:
        sys.stderr.write(f"quality_check: syntax error in {file_path}:\n{exc}\n")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
