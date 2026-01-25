# Claude Remote Bridge

**Bidirectional remote communication with Claude Code via ntfy**

Ever needed to nudge your local Claude Code session while away from your machine? This bridge enables remote communication through [ntfy.sh](https://ntfy.sh) - send commands, receive status updates, and stay connected to your AI pair programmer from anywhere.

```
┌─────────────────┐     ┌─────────────┐     ┌─────────────────┐
│  You (Phone)    │────▶│   ntfy.sh   │────▶│  Bridge Daemon  │
│                 │◀────│             │◀────│                 │
└─────────────────┘     └─────────────┘     └────────┬────────┘
                                                     │
                                            ┌────────▼────────┐
                                            │  Claude Code    │
                                            │  (local session)│
                                            └─────────────────┘
```

## The Problem

When running long tasks with Claude Code (training ML models, deployments, etc.), you might:
- Step away from your machine
- Want to check progress from your phone
- Need to give Claude a "go ahead" or "stop" command
- Be stuck waiting for user input you can't provide remotely

## The Solution

Claude Remote Bridge creates a bidirectional channel:
- **Incoming**: Messages you send to ntfy appear in Claude's inbox
- **Outgoing**: Claude can send status updates back to ntfy (your phone)

## Installation

```bash
# Clone the repo
git clone https://github.com/ARTIFACTIQ/claude-remote-bridge.git
cd claude-remote-bridge

# Install dependencies
pip install requests

# Add CLI to path (optional)
chmod +x src/crb
ln -s $(pwd)/src/crb /usr/local/bin/crb
```

## Quick Start

### 1. Start the Bridge

```bash
# Pick a unique topic name (like a private channel)
crb start my-secret-claude-topic

# Or run directly
python src/bridge.py --topic my-secret-claude-topic
```

### 2. Send Messages from Your Phone

Use the ntfy app or any HTTP client:

```bash
# From your phone/anywhere
curl -d "proceed with deployment" ntfy.sh/my-secret-claude-topic

# Or use the ntfy mobile app
```

### 3. Claude Checks for Messages

In your Claude Code session, Claude can check for messages:

```python
from claude_integration import check_inbox, reply

# Check for new messages
messages = check_inbox()
for msg in messages:
    print(f"Remote user says: {msg['message']}")

# Send a reply
reply("Acknowledged! Starting deployment now.", title="Claude")
```

### 4. Receive Updates on Your Phone

Subscribe to the topic in the ntfy app to receive Claude's responses and status updates.

## CLI Reference

```bash
crb start <topic>     # Start the bridge daemon
crb stop              # Stop the bridge daemon
crb status            # Show bridge status
crb inbox             # Check inbox for messages
crb send <message>    # Send a message (for testing)
crb clear             # Clear inbox
crb logs              # Show bridge logs
```

## Integration with Claude Code

### As a Hook (Recommended)

Add to your Claude Code hooks to auto-check inbox:

```json
// .claude/hooks.json
{
  "pre_tool_call": [
    {
      "command": "python /path/to/claude-remote-bridge/src/claude_integration.py",
      "description": "Check for remote messages"
    }
  ]
}
```

### Manual Check

Ask Claude to check the inbox:
> "Check the remote inbox for any messages"

Claude can then use the integration module to read messages.

### In Python Scripts

```python
from src.claude_integration import check_inbox, reply, get_inbox_summary

# Check for messages
messages = check_inbox()

# Get summary without marking as read
summary = get_inbox_summary()
print(f"Unread: {summary['unread']}")

# Send responses
reply("Task completed!", priority="high", tags="success")
```

## Message Format

### Incoming (to Claude)

Messages are stored in `~/.claude_inbox` as JSON lines:

```json
{
  "id": "abc123",
  "timestamp": "2024-01-25T10:30:00",
  "title": "User Command",
  "message": "proceed with training",
  "tags": ["command"],
  "priority": 3,
  "read": false
}
```

### Outgoing (from Claude)

Write to `~/.claude_outbox` for the bridge to send:

```json
{
  "message": "Training complete!",
  "title": "Claude Status",
  "priority": "high",
  "tags": "success,training"
}
```

## Security Considerations

- **Topic names are public** - use unique, hard-to-guess names
- **No authentication** - anyone who knows your topic can send messages
- **Local files** - inbox/outbox are stored locally with user permissions

For sensitive use cases, consider:
- Using random topic names: `my-claude-$(openssl rand -hex 8)`
- Running your own ntfy server
- Adding message signing/verification

## Use Cases

1. **ML Training Monitoring**
   - Receive epoch updates on your phone
   - Send "stop" to halt training early
   - Get notified when training completes

2. **Deployment Approval**
   - Claude asks for approval before deploying
   - You send "approved" from anywhere
   - Claude proceeds with deployment

3. **Long-Running Tasks**
   - Check progress remotely
   - Provide input when Claude is stuck
   - Receive completion notifications

4. **Pair Programming**
   - Multiple people can send suggestions to Claude
   - Collaborative remote coding sessions

## Troubleshooting

**Bridge won't start**
```bash
crb logs  # Check for errors
```

**Messages not appearing**
```bash
# Test ntfy directly
curl -d "test" ntfy.sh/your-topic

# Check inbox file
cat ~/.claude_inbox
```

**Claude not seeing messages**
- Ensure bridge is running: `crb status`
- Check file permissions on `~/.claude_inbox`

## Contributing

Contributions welcome! Please open issues or PRs on GitHub.

## License

MIT License - see [LICENSE](LICENSE)

## Credits

- [ntfy.sh](https://ntfy.sh) - Simple pub-sub notifications
- [Claude Code](https://claude.ai/claude-code) - AI pair programming
- [ARTIFACTIQ](https://github.com/ARTIFACTIQ) - Building AI tools

---

Made with AI by ARTIFACTIQ
