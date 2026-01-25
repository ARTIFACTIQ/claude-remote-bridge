"""Claude Remote Bridge - Bidirectional communication with Claude Code via ntfy"""

from .claude_integration import (
    check_inbox,
    reply,
    clear_inbox,
    get_inbox_summary,
    format_messages,
    inbox,
)
from .bridge import ClaudeRemoteBridge

__version__ = "1.0.0"
__all__ = [
    "ClaudeRemoteBridge",
    "check_inbox",
    "reply",
    "clear_inbox",
    "get_inbox_summary",
    "format_messages",
    "inbox",
]
