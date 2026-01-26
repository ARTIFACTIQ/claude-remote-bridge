#!/usr/bin/env python3
"""
Claude Remote Bridge - Bidirectional communication with Claude Code via ntfy

This daemon polls a ntfy topic for incoming messages and writes them to a local
inbox file that Claude Code can read. Enables remote communication with local
Claude Code sessions.

Usage:
    # Start the bridge daemon
    python bridge.py --topic my-claude-inbox

    # Or with custom inbox location
    python bridge.py --topic my-claude-inbox --inbox ~/.claude_inbox

    # Run as background daemon
    python bridge.py --topic my-claude-inbox --daemon
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Thread, Event
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)

# Import query handler
try:
    from query_handler import handle_query
except ImportError:
    # Fallback if not in same directory
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from query_handler import handle_query
    except ImportError:
        handle_query = None


DEFAULT_INBOX = Path.home() / ".claude_inbox"
DEFAULT_OUTBOX = Path.home() / ".claude_outbox"
NTFY_BASE_URL = "https://ntfy.sh"


class ClaudeRemoteBridge:
    """Bidirectional bridge between ntfy and local Claude Code session."""

    def __init__(
        self,
        topic: str,
        inbox_path: Path = DEFAULT_INBOX,
        outbox_path: Path = DEFAULT_OUTBOX,
        poll_interval: int = 5,
        notify_topic: Optional[str] = None,
    ):
        self.topic = topic
        self.notify_topic = notify_topic or topic  # Topic for query responses
        self.inbox_path = Path(inbox_path)
        self.outbox_path = Path(outbox_path)
        self.poll_interval = poll_interval
        self.stop_event = Event()
        self.last_message_id: Optional[str] = None

        # Ensure inbox/outbox exist
        self.inbox_path.parent.mkdir(parents=True, exist_ok=True)
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)

    def poll_ntfy(self) -> list:
        """Poll ntfy for new messages."""
        try:
            url = f"{NTFY_BASE_URL}/{self.topic}/json"
            params = {"poll": "1", "since": "30s"}

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                messages = []
                for line in response.text.strip().split("\n"):
                    if line:
                        try:
                            msg = json.loads(line)
                            if msg.get("event") == "message":
                                messages.append(msg)
                        except json.JSONDecodeError:
                            continue
                return messages
            return []

        except requests.RequestException as e:
            print(f"[{self._timestamp()}] Poll error: {e}")
            return []

    def write_to_inbox(self, message: dict):
        """Write a message to the inbox file."""
        timestamp = datetime.now().isoformat()
        msg_id = message.get("id", "unknown")
        title = message.get("title", "")
        body = message.get("message", "")
        tags = message.get("tags", [])
        priority = message.get("priority", 3)

        entry = {
            "id": msg_id,
            "timestamp": timestamp,
            "title": title,
            "message": body,
            "tags": tags,
            "priority": priority,
            "read": False,
        }

        # Append to inbox (JSON lines format)
        with open(self.inbox_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"[{self._timestamp()}] Received: {title or body[:50]}")

    def process_query(self, message: dict) -> bool:
        """
        Check if message is a query and process it.

        Returns True if it was a query (handled), False otherwise.
        """
        if handle_query is None:
            return False

        body = message.get("message", "")
        result = handle_query(body)

        if result is None:
            return False

        # Send query response to notify topic
        print(f"[{self._timestamp()}] Query: {body[:30]}...")
        self.send_to_ntfy(
            result["response"],
            title=result.get("title", "Query Result"),
            tags=result.get("tags", "robot"),
            topic=self.notify_topic,
        )
        print(f"[{self._timestamp()}] Response sent to {self.notify_topic}")
        return True

    def send_to_ntfy(self, message: str, title: str = "", priority: str = "default", tags: str = "", topic: Optional[str] = None):
        """Send a message to ntfy topic."""
        target_topic = topic or self.topic
        try:
            headers = {"Title": title} if title else {}
            if priority:
                headers["Priority"] = priority
            if tags:
                headers["Tags"] = tags

            response = requests.post(
                f"{NTFY_BASE_URL}/{target_topic}",
                data=message.encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            return response.status_code == 200

        except requests.RequestException as e:
            print(f"[{self._timestamp()}] Send error: {e}")
            return False

    def check_outbox(self):
        """Check outbox for messages to send."""
        if not self.outbox_path.exists():
            return

        try:
            with open(self.outbox_path, "r") as f:
                lines = f.readlines()

            if not lines:
                return

            # Process each outgoing message
            sent = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                    if self.send_to_ntfy(
                        msg.get("message", ""),
                        msg.get("title", ""),
                        msg.get("priority", "default"),
                        msg.get("tags", ""),
                    ):
                        sent.append(line)
                except json.JSONDecodeError:
                    # Plain text message
                    if self.send_to_ntfy(line):
                        sent.append(line)

            # Clear sent messages from outbox
            if sent:
                remaining = [l for l in lines if l.strip() and l.strip() not in sent]
                with open(self.outbox_path, "w") as f:
                    f.writelines(remaining)

        except Exception as e:
            print(f"[{self._timestamp()}] Outbox error: {e}")

    def run(self):
        """Main polling loop."""
        print(f"[{self._timestamp()}] Claude Remote Bridge started")
        print(f"  Topic: {self.topic}")
        print(f"  Inbox: {self.inbox_path}")
        print(f"  Outbox: {self.outbox_path}")
        print(f"  Poll interval: {self.poll_interval}s")
        print(f"  Press Ctrl+C to stop\n")

        # Send startup notification
        self.send_to_ntfy(
            f"Bridge started\nInbox: {self.inbox_path}",
            title="Claude Remote Bridge",
            tags="bridge,white_check_mark",
        )

        seen_ids = set()

        while not self.stop_event.is_set():
            try:
                # Poll for incoming messages
                messages = self.poll_ntfy()
                for msg in messages:
                    msg_id = msg.get("id")
                    if msg_id and msg_id not in seen_ids:
                        # Skip our own startup message
                        if "Bridge started" not in msg.get("message", ""):
                            # Check if it's a query - if so, process and respond
                            if not self.process_query(msg):
                                # Not a query, write to inbox for Claude
                                self.write_to_inbox(msg)
                        seen_ids.add(msg_id)

                # Check outbox for outgoing messages
                self.check_outbox()

                # Wait before next poll
                self.stop_event.wait(self.poll_interval)

            except KeyboardInterrupt:
                break

        print(f"\n[{self._timestamp()}] Bridge stopped")

    def stop(self):
        """Stop the bridge."""
        self.stop_event.set()

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%H:%M:%S")


def read_inbox(inbox_path: Path = DEFAULT_INBOX, unread_only: bool = True, mark_read: bool = True) -> list:
    """
    Read messages from inbox. Utility function for Claude Code integration.

    Args:
        inbox_path: Path to inbox file
        unread_only: Only return unread messages
        mark_read: Mark returned messages as read

    Returns:
        List of message dicts
    """
    if not inbox_path.exists():
        return []

    messages = []
    updated_lines = []

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

    return messages


def write_outbox(message: str, title: str = "", priority: str = "default", tags: str = "", outbox_path: Path = DEFAULT_OUTBOX):
    """
    Write a message to outbox for sending. Utility function for Claude Code.

    Args:
        message: Message body
        title: Optional title
        priority: Priority level (min, low, default, high, max)
        tags: Comma-separated tags
        outbox_path: Path to outbox file
    """
    entry = {
        "message": message,
        "title": title,
        "priority": priority,
        "tags": tags,
        "timestamp": datetime.now().isoformat(),
    }

    with open(outbox_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def clear_inbox(inbox_path: Path = DEFAULT_INBOX):
    """Clear all messages from inbox."""
    if inbox_path.exists():
        inbox_path.unlink()


def daemonize():
    """Fork into background daemon."""
    if os.fork() > 0:
        sys.exit(0)

    os.setsid()

    if os.fork() > 0:
        sys.exit(0)

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    with open("/dev/null", "r") as devnull:
        os.dup2(devnull.fileno(), sys.stdin.fileno())

    log_file = Path.home() / ".claude_bridge.log"
    with open(log_file, "a") as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())


def main():
    parser = argparse.ArgumentParser(
        description="Claude Remote Bridge - Bidirectional ntfy communication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--topic", "-t",
        required=True,
        help="ntfy topic to subscribe to (e.g., my-claude-inbox)",
    )
    parser.add_argument(
        "--inbox", "-i",
        type=Path,
        default=DEFAULT_INBOX,
        help=f"Path to inbox file (default: {DEFAULT_INBOX})",
    )
    parser.add_argument(
        "--outbox", "-o",
        type=Path,
        default=DEFAULT_OUTBOX,
        help=f"Path to outbox file (default: {DEFAULT_OUTBOX})",
    )
    parser.add_argument(
        "--poll-interval", "-p",
        type=int,
        default=5,
        help="Poll interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--notify-topic", "-n",
        type=str,
        default=None,
        help="Topic for query responses (default: same as --topic)",
    )
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="Run as background daemon",
    )

    args = parser.parse_args()

    if args.daemon:
        daemonize()
        pid_file = Path.home() / ".claude_bridge.pid"
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))

    bridge = ClaudeRemoteBridge(
        topic=args.topic,
        inbox_path=args.inbox,
        outbox_path=args.outbox,
        poll_interval=args.poll_interval,
        notify_topic=args.notify_topic,
    )

    # Handle signals
    def signal_handler(sig, frame):
        bridge.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    bridge.run()


if __name__ == "__main__":
    main()
