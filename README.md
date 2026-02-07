# Claude Remote Bridge

**Bidirectional remote communication with Claude Code via ntfy.sh**

Send commands, query status, and receive updates from your local Claude Code session - from anywhere. Built for long-running AI tasks like ML training where you need to step away but stay connected.

## Architecture

```
                         REMOTE                                        LOCAL MACHINE
                    (Phone / Laptop)                              (Running Claude Code)

    ┌───────────────────────┐               ┌──────────────────────────────────────────────┐
    │                       │               │                                              │
    │  ntfy App / curl      │               │   Bridge Daemon (bridge.py)                  │
    │                       │               │   ┌────────────────────────────────────────┐  │
    │  ┌─────────────────┐  │               │   │                                        │  │
    │  │ Send message     │──┼──── POST ────┼──▶│  Poll ntfy.sh every 5s                 │  │
    │  │ "proceed"        │  │   ntfy.sh    │   │  ┌──────────┐    ┌───────────────────┐ │  │
    │  └─────────────────┘  │               │   │  │ Query?   │───▶│ query_handler.py  │ │  │
    │                       │               │   │  │ (q:train) │    │ - training status │ │  │
    │  ┌─────────────────┐  │               │   │  └────┬─────┘    │ - disk / procs    │ │  │
    │  │ Receive updates  │◀─┼──── POST ────┼───│       │          │ - logs / tasks    │ │  │
    │  │ "Epoch 5/15..."  │  │   ntfy.sh    │   │       ▼          └───────────────────┘ │  │
    │  └─────────────────┘  │               │   │  ~/.claude_inbox     (JSON lines)      │  │
    │                       │               │   │       │                                 │  │
    │  ┌─────────────────┐  │               │   │  ~/.claude_outbox ◀──── reply()        │  │
    │  │ Query status     │──┼──── POST ────┼──▶│       │                   ▲             │  │
    │  │ "q: training"    │  │   ntfy.sh    │   └───────┼───────────────────┼─────────────┘  │
    │  └─────────────────┘  │               │           │                   │                │
    │                       │               │           ▼                   │                │
    └───────────────────────┘               │   ┌───────────────────────────────────────┐   │
                                            │   │           Claude Code Session          │   │
                                            │   │                                       │   │
                                            │   │  Hook (UserPromptSubmit):              │   │
                                            │   │    auto-checks inbox on every message  │   │
                                            │   │                                       │   │
                                            │   │  check_inbox() ──▶ read messages      │   │
                                            │   │  reply()        ──▶ send responses    │   │
                                            │   └───────────────────────────────────────┘   │
                                            └──────────────────────────────────────────────┘
```

### How It Works

1. **Bridge daemon** runs in the background, polling ntfy.sh every 5 seconds
2. **Incoming messages** land in `~/.claude_inbox` (JSON lines file)
3. **Query messages** (prefixed `q:` or `query:`) are intercepted and answered directly
4. **Claude Code hook** auto-reads the inbox on every user interaction
5. **Outgoing replies** queue in `~/.claude_outbox`, picked up and sent by the bridge

## The Problem

When running long tasks with Claude Code (ML training, deployments, data pipelines), you need to:
- Step away from your machine but stay informed
- Check progress from your phone
- Send approvals or commands remotely
- Avoid losing context when Claude is waiting for input

## Installation

```bash
git clone https://github.com/ARTIFACTIQ/claude-remote-bridge.git
cd claude-remote-bridge
pip install requests

# Add CLI to path
chmod +x src/crb
ln -s $(pwd)/src/crb /usr/local/bin/crb
```

## Quick Start

### 1. Start the Bridge

```bash
crb start my-secret-topic
```

### 2. Install the Hook

```bash
python3 src/install_hook.py
```

This adds a hook to `~/.claude/hooks.json` that auto-checks the inbox on every Claude Code interaction.

### 3. Send Messages from Anywhere

```bash
# From your phone or any device
curl -d "proceed with deployment" ntfy.sh/my-secret-topic

# Query training status
curl -d "q: training" ntfy.sh/my-secret-topic

# High priority
curl -d "STOP training" -H "Priority: high" ntfy.sh/my-secret-topic
```

Or use the [ntfy mobile app](https://ntfy.sh) (iOS/Android).

### 4. Claude Sees Your Messages

Next time Claude Code processes any user input, the hook fires and displays:

```
=== 1 new message(s) ===
[2026-02-07 14:30] proceed with deployment
```

### 5. Claude Can Reply

```python
from src.claude_integration import reply
reply("Deployment complete!", priority="high", tags="success")
```

You receive the notification on your phone via ntfy.

## Built-in Query System

Send `query:` or `q:` prefixed messages for instant responses - no Claude interaction needed:

| Query | What It Returns |
|-------|----------------|
| `q: training` | Current epoch, completion %, loss metrics |
| `q: tasks` | Running processes (training, bridge, monitor) |
| `q: disk` | Disk usage and available space |
| `q: processes` | Top Python processes with CPU/MEM |
| `q: logs 20` | Last 20 lines of training log |
| `q: help` | List of available queries |

The bridge intercepts these and responds directly via ntfy - no need to be at the keyboard.

## CLI Reference

```bash
crb start <topic>     # Start the bridge daemon
crb stop              # Stop the bridge daemon
crb status            # Show bridge status and message counts
crb inbox             # Check inbox for messages
crb send <message>    # Send a message via ntfy
crb clear             # Clear inbox
crb logs              # Show bridge daemon logs
crb hook              # Install Claude Code hook
crb unhook            # Remove Claude Code hook
```

## Claude Code Integration

### Hook Configuration

The hook (`~/.claude/hooks.json`) runs on every user message:

```json
{
  "UserPromptSubmit": [
    {
      "command": "python3 ~/claude-remote-bridge/src/claude_integration.py 2>/dev/null | head -20",
      "timeout": 5000
    }
  ]
}
```

### Programmatic API

```python
from src.claude_integration import check_inbox, reply, get_inbox_summary

# Check for new messages
messages = check_inbox()
for msg in messages:
    print(f"Remote: {msg['message']}")

# Get summary without marking as read
summary = get_inbox_summary()
print(f"Unread: {summary['unread']}")

# Send response
reply("Training complete!", priority="high", tags="success")
```

## Limitations

Claude Code cannot be interrupted externally. The bridge works within this constraint:

| Scenario | Solution |
|----------|----------|
| Claude waiting for input | Send ntfy message + type anything in chat |
| Claude running a long task | Ask Claude to check inbox periodically |
| Need instant status | Use `q: training` queries (bridge answers directly) |

**Workaround for long tasks:** Ask Claude to check the inbox every N minutes:
> "Check the remote inbox every 10 minutes during training"

## Message Format

**Inbox** (`~/.claude_inbox`) - JSON lines:
```json
{"id": "abc123", "timestamp": "2026-02-07T14:30:00", "message": "proceed", "priority": 3, "read": false}
```

**Outbox** (`~/.claude_outbox`) - JSON lines:
```json
{"message": "Training complete!", "title": "Status", "priority": "high", "tags": "success"}
```

## Security

- **Topic names are public** - use unique, hard-to-guess names
- **No authentication** - anyone who knows your topic can send messages
- **Local files only** - inbox/outbox stored with user permissions

For sensitive environments:
```bash
# Generate a random topic name
crb start my-claude-$(openssl rand -hex 8)
```

Or run your own [ntfy server](https://docs.ntfy.sh/install/).

## Use Cases

- **ML Training** - Monitor epochs, send stop commands, get notified on completion
- **Deployment Approval** - Approve production deployments from your phone
- **Long Pipelines** - Check progress on data processing, builds, migrations
- **Remote Pair Programming** - Multiple people can send input to a shared Claude session

## Troubleshooting

```bash
crb status            # Is bridge running?
crb logs              # Check for errors
curl -d "test" ntfy.sh/your-topic   # Test ntfy connectivity
cat ~/.claude_inbox   # Check inbox directly
```

## License

MIT License - see [LICENSE](LICENSE)

## Credits

- [ntfy.sh](https://ntfy.sh) - Simple pub-sub notifications
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) - AI coding agent
- [ARTIFACTIQ](https://github.com/ARTIFACTIQ) - AI-powered fashion recognition

---

Made with AI by [ARTIFACTIQ](https://artifactiq.ai)
