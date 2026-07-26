"""Claude Code wrapper: dv claude."""

import os
import subprocess
import sys


def run_claude():
    """Launch Claude Code with DataVeil gateway as upstream."""
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:8787"
    # Remove direct key reference — gateway holds it
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    subprocess.run(["claude"] + sys.argv[1:], env=env)
