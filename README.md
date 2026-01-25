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

### Automatic Hook (Recommended)

Install the hook to make Claude Code auto-check the inbox on every message:

```bash
# Automatic installation
python src/install_hook.py

# Or manual: copy to ~/.claude/hooks.json
cp examples/hooks.json ~/.claude/hooks.json
```

The hook configuration (`~/.claude/hooks.json`):

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

**What this does:** Every time you send a message to Claude Code, it first checks the remote inbox and displays any new messages. This means:

1. Send a message via ntfy from your phone
2. Send ANY message in Claude Code (even just "." or "continue")
3. Claude sees your ntfy message automatically

### Hook Management

```bash
# Install hook
python src/install_hook.py

# Reinstall/update hook
python src/install_hook.py --force

# Uninstall hook
python src/install_hook.py --uninstall

# Specify custom bridge path
python src/install_hook.py --bridge-path /custom/path
```

### Manual Check

Ask Claude to check the inbox:
> "Check the remote inbox for any messages"

Or Claude can use the integration module directly:

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

## Important Limitations

### The "Nudge" Problem

**Q: Can I nudge Claude remotely when it's stuck?**

**A: Partially.** Here's the reality:

```
You send ntfy ──▶ Bridge writes to ~/.claude_inbox ──▶ Claude checks on next interaction
                                                              │
                                                              ▼
                                                    Claude does NOT auto-wake
                                                    You must trigger a check
```

| Scenario | What Works |
|----------|------------|
| Claude waiting for your input | Send ntfy + send anything here (".", "continue") |
| Claude running a long task | Claude should periodically check inbox in workflow |
| Claude completely idle | Send ntfy + send anything to wake Claude |

### Why This Limitation Exists

Claude Code doesn't have:
- Background polling/listening capability
- Ability to interrupt itself
- Push notification reception

The hook helps by checking inbox on EVERY user message, but you still need to send *something* in the chat to trigger it.

### Workarounds

1. **For long tasks:** Ask Claude to check inbox periodically
   > "Check the remote inbox every 10 minutes during training"

2. **For approvals:** Send ntfy message, then send "." in chat
   ```
   Phone: curl -d "approved" ntfy.sh/my-topic
   Chat:  .
   Claude sees: "approved" from remote inbox
   ```

3. **Future improvement:** Claude Code could add native remote messaging (feature request to Anthropic)

### Best Practices

1. **Use separate topics** for cleaner communication:
   - `my-claude-inbox` - messages TO Claude
   - `my-claude-outbox` - messages FROM Claude (subscribe on phone)

2. **Keep messages short** - they're displayed in Claude's context

3. **Use priority levels** for important messages:
   ```bash
   curl -d "URGENT: stop training" -H "Priority: high" ntfy.sh/topic
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
