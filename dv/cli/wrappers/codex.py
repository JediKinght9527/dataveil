"""Codex CLI wrapper: dv codex."""

import os
import subprocess
import sys


def run_codex():
    """Launch Codex CLI with DataVeil gateway as upstream."""
    env = os.environ.copy()
    env["OPENAI_BASE_URL"] = "http://127.0.0.1:8787/v1"
    env.pop("OPENAI_API_KEY", None)
    subprocess.run(["codex"] + sys.argv[1:], env=env)
