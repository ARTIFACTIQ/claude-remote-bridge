#!/usr/bin/env python3
"""
Claude Code Integration for Remote Bridge

This module provides functions for Claude Code to interact with the remote bridge.
Can be used directly or as part of a Claude Code hook.

Usage in Claude Code:
    # Check for new messages
    from claude_integration import check_inbox, reply

    messages = check_inbox()
    if messages:
        for msg in messages:
            print(f"Remote: {msg['message']}")
        reply("Acknowledged!", title="Claude")
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

DEFAULT_INBOX = Path.home() / ".claude_inbox"
DEFAULT_OUTBOX = Path.home() / ".claude_outbox"
NTFY_TOPIC = os.getenv("CLAUDE_BRIDGE_TOPIC", "")


def check_inbox(
    inbox_path: Path = DEFAULT_INBOX,
    unread_only: bool = True,
    mark_read: bool = True
) -> List[Dict]:
    """
    Check inbox for new messages from remote user.

    Args:
        inbox_path: Path to inbox file
        unread_only: Only return unread messages
        mark_read: Mark messages as read after returning

    Returns:
        List of message dictionaries with keys:
        - id: Message ID
        - timestamp: When received
        - title: Message title (may be empty)
        - message: Message body
        - tags: List of tags
        - priority: Priority level (1-5)
        - read: Whether message has been read
    """
    inbox_path = Path(inbox_path)

    if not inbox_path.exists():
        return []

    messages = []
    updated_lines = []

    try:
        with open(inbox_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)

                    if unread_only and msg.get("read", False):
                        updated_lines.append(json.dumps(msg) + "\n")
                        continue

                    messages.append(msg)

                    if mark_read:
                        msg["read"] = True

                    updated_lines.append(json.dumps(msg) + "\n")

                except json.JSONDecodeError:
                    updated_lines.append(line + "\n")

        # Update file with read status
        if mark_read and messages:
            with open(inbox_path, "w") as f:
                f.writelines(updated_lines)

    except Exception as e:
        print(f"Error reading inbox: {e}")

    return messages


def reply(
    message: str,
    title: str = "Claude",
    priority: str = "default",
    tags: str = "",
    outbox_path: Path = DEFAULT_OUTBOX
) -> bool:
    """
    Send a reply to the remote user via the bridge.

    Args:
        message: Message body
        title: Message title
        priority: Priority (min, low, default, high, max)
        tags: Comma-separated tags
        outbox_path: Path to outbox file

    Returns:
        True if message was queued successfully
    """
    outbox_path = Path(outbox_path)

    try:
        entry = {
            "message": message,
            "title": title,
            "priority": priority,
            "tags": tags,
            "timestamp": datetime.now().isoformat(),
        }

        outbox_path.parent.mkdir(parents=True, exist_ok=True)

        with open(outbox_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return True

    except Exception as e:
        print(f"Error writing to outbox: {e}")
        return False


def clear_inbox(inbox_path: Path = DEFAULT_INBOX) -> bool:
    """Clear all messages from inbox."""
    try:
        inbox_path = Path(inbox_path)
        if inbox_path.exists():
            inbox_path.unlink()
        return True
    except Exception as e:
        print(f"Error clearing inbox: {e}")
        return False


def get_inbox_summary(inbox_path: Path = DEFAULT_INBOX) -> Dict:
    """
    Get summary of inbox status.

    Returns:
        Dict with keys:
        - total: Total message count
        - unread: Unread message count
        - latest: Most recent message (if any)
    """
    inbox_path = Path(inbox_path)

    if not inbox_path.exists():
        return {"total": 0, "unread": 0, "latest": None}

    total = 0
    unread = 0
    latest = None

    try:
        with open(inbox_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                    total += 1
                    if not msg.get("read", False):
                        unread += 1
                    latest = msg
                except json.JSONDecodeError:
                    continue

    except Exception:
        pass

    return {"total": total, "unread": unread, "latest": latest}


def format_messages(messages: List[Dict]) -> str:
    """Format messages for display."""
    if not messages:
        return "No new messages."

    lines = [f"=== {len(messages)} new message(s) ===\n"]

    for msg in messages:
        timestamp = msg.get("timestamp", "")[:19]  # Trim to seconds
        title = msg.get("title", "")
        body = msg.get("message", "")
        priority = msg.get("priority", 3)

        priority_icon = {1: "⬇️", 2: "↓", 3: "", 4: "↑", 5: "⬆️"}.get(priority, "")

        if title:
            lines.append(f"[{timestamp}] {priority_icon} {title}")
            lines.append(f"  {body}\n")
        else:
            lines.append(f"[{timestamp}] {priority_icon} {body}\n")

    return "\n".join(lines)


# Convenience function for quick inbox check
def inbox() -> str:
    """Quick check inbox and return formatted messages."""
    messages = check_inbox()
    return format_messages(messages)


if __name__ == "__main__":
    # CLI mode - check inbox and print messages
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "reply":
        # Send a reply
        if len(sys.argv) > 2:
            message = " ".join(sys.argv[2:])
            if reply(message):
                print(f"Queued: {message}")
            else:
                print("Failed to queue message")
        else:
            print("Usage: python claude_integration.py reply <message>")
    else:
        # Check inbox
        print(inbox())
