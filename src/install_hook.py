#!/usr/bin/env python3
"""
Install Claude Code hook for automatic inbox checking.

This script installs a hook that makes Claude Code automatically check
the remote inbox whenever you send a message.

Usage:
    python install_hook.py

    # Or specify custom paths
    python install_hook.py --bridge-path /custom/path/to/bridge
"""

import argparse
import json
import os
from pathlib import Path


CLAUDE_HOOKS_DIR = Path.home() / ".claude"
CLAUDE_HOOKS_FILE = CLAUDE_HOOKS_DIR / "hooks.json"

DEFAULT_HOOK = {
    "UserPromptSubmit": [
        {
            "command": "python3 {bridge_path}/src/claude_integration.py 2>/dev/null | head -20",
            "timeout": 5000
        }
    ]
}


def get_bridge_path() -> Path:
    """Get the path to the bridge installation."""
    # Check common locations
    candidates = [
        Path(__file__).parent.parent,  # Relative to this script
        Path.home() / "claude-remote-bridge",
        Path("/usr/local/share/claude-remote-bridge"),
        Path.cwd(),
    ]

    for path in candidates:
        if (path / "src" / "claude_integration.py").exists():
            return path.resolve()

    return Path(__file__).parent.parent.resolve()


def load_existing_hooks() -> dict:
    """Load existing hooks configuration."""
    if CLAUDE_HOOKS_FILE.exists():
        try:
            with open(CLAUDE_HOOKS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def install_hook(bridge_path: Path, force: bool = False) -> bool:
    """Install the inbox check hook."""

    # Create hooks directory if needed
    CLAUDE_HOOKS_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing hooks
    hooks = load_existing_hooks()

    # Check if hook already exists
    if "UserPromptSubmit" in hooks and not force:
        existing = hooks["UserPromptSubmit"]
        for hook in existing:
            if "claude_integration.py" in hook.get("command", ""):
                print("Hook already installed. Use --force to reinstall.")
                return False

    # Create hook command
    command = f"python3 {bridge_path}/src/claude_integration.py 2>/dev/null | head -20"

    new_hook = {
        "command": command,
        "timeout": 5000
    }

    # Add to existing hooks
    if "UserPromptSubmit" not in hooks:
        hooks["UserPromptSubmit"] = []

    # Remove old bridge hooks if forcing
    if force:
        hooks["UserPromptSubmit"] = [
            h for h in hooks["UserPromptSubmit"]
            if "claude_integration.py" not in h.get("command", "")
        ]

    hooks["UserPromptSubmit"].append(new_hook)

    # Write hooks file
    with open(CLAUDE_HOOKS_FILE, "w") as f:
        json.dump(hooks, f, indent=2)

    print(f"Hook installed successfully!")
    print(f"  Hooks file: {CLAUDE_HOOKS_FILE}")
    print(f"  Bridge path: {bridge_path}")
    print()
    print("Claude Code will now auto-check inbox on each message.")
    print("Restart Claude Code for the hook to take effect.")

    return True


def uninstall_hook() -> bool:
    """Remove the inbox check hook."""
    if not CLAUDE_HOOKS_FILE.exists():
        print("No hooks file found.")
        return False

    hooks = load_existing_hooks()

    if "UserPromptSubmit" not in hooks:
        print("No UserPromptSubmit hooks found.")
        return False

    original_count = len(hooks["UserPromptSubmit"])
    hooks["UserPromptSubmit"] = [
        h for h in hooks["UserPromptSubmit"]
        if "claude_integration.py" not in h.get("command", "")
    ]

    removed = original_count - len(hooks["UserPromptSubmit"])

    if removed == 0:
        print("Bridge hook not found.")
        return False

    # Clean up empty arrays
    if not hooks["UserPromptSubmit"]:
        del hooks["UserPromptSubmit"]

    # Write or delete hooks file
    if hooks:
        with open(CLAUDE_HOOKS_FILE, "w") as f:
            json.dump(hooks, f, indent=2)
    else:
        CLAUDE_HOOKS_FILE.unlink()

    print(f"Hook uninstalled. Removed {removed} hook(s).")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Install Claude Code hook for remote inbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--bridge-path", "-p",
        type=Path,
        default=None,
        help="Path to claude-remote-bridge installation",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force reinstall even if hook exists",
    )
    parser.add_argument(
        "--uninstall", "-u",
        action="store_true",
        help="Remove the hook instead of installing",
    )

    args = parser.parse_args()

    if args.uninstall:
        uninstall_hook()
        return

    bridge_path = args.bridge_path or get_bridge_path()

    # Verify bridge exists
    integration_file = bridge_path / "src" / "claude_integration.py"
    if not integration_file.exists():
        print(f"Error: claude_integration.py not found at {integration_file}")
        print("Please specify --bridge-path or install from the correct directory.")
        return

    install_hook(bridge_path, args.force)


if __name__ == "__main__":
    main()
