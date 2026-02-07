# How We Stay Connected to 14-Hour AI Training Runs From Our Phone

At ARTIFACTIQ, we use Claude Code as our AI pair programmer for everything from writing training scripts to managing deployments. But when we kicked off a 14-hour YOLO model training run across 46 data shards, we hit a problem: **you can't just walk away from an AI agent and expect it to figure everything out.**

Claude Code needed approvals. Training shards failed and needed retries. We wanted to check progress without sitting at the terminal all day.

So we built **Claude Remote Bridge** - a lightweight tool that lets you communicate with your local Claude Code session from anywhere, using nothing but your phone.

## The Problem

Claude Code is a powerful local agent, but it has one fundamental constraint: **it can't be interrupted or nudged externally**. There's no push notification, no webhook, no way to send it a message while it's working.

When training ML models that run for hours, this creates real friction:
- Training finishes at 2am - you don't find out until morning
- A shard fails and Claude needs your decision on retry strategy
- You want to check loss curves from the coffee shop
- You need to say "stop" before the model overfits further

## The Solution: ntfy.sh as a Message Bus

We built a bridge daemon that uses [ntfy.sh](https://ntfy.sh) - a simple, open-source pub/sub notification service - as a bidirectional message channel between your phone and Claude Code.

The architecture is straightforward:

**Your Phone** --> ntfy.sh --> **Bridge Daemon** --> **Claude Code Session**

And back:

**Claude Code** --> Bridge Daemon --> ntfy.sh --> **Your Phone**

The bridge daemon polls ntfy.sh every 5 seconds and writes incoming messages to a local inbox file. A Claude Code hook automatically checks this inbox on every interaction. Going the other way, Claude writes to an outbox file, and the bridge picks it up and posts it back to ntfy.

## The Query System

The real power comes from built-in queries. Send `q: training` from your phone and the bridge answers directly - without needing Claude to be active:

```
You: "q: training"
Bridge: "Epoch 5/15 - 35% complete | Box: 2.3 | Cls: 1.9 | DFL: 0.8"
```

Other queries include disk space, running processes, and log tails. All answered by the bridge daemon in seconds.

## How We Actually Use It

Last week we ran E9 training - 46 shards of 1,500 images each, sequential fine-tuning on Apple M4 Max. We started the bridge, walked away, and monitored the entire run from our phone:

- **Hour 3**: `q: training` - "Shard 15/46, loss trending down"
- **Hour 8**: `q: logs` - noticed early stopping on shard 21
- **Hour 12**: Got ntfy notification: "7 early-stopped shards, running weighted avg retry"
- **Hour 14**: "E9 complete. Best mAP50=0.040, +22% over E8.1. RELEASE candidate."

We sent "approved" from our phone. Claude exported the model, updated the docs, and tagged the release. All without touching the keyboard.

## Open Source

We've open-sourced Claude Remote Bridge at [github.com/ARTIFACTIQ/claude-remote-bridge](https://github.com/ARTIFACTIQ/claude-remote-bridge).

It's simple to set up:

```bash
git clone https://github.com/ARTIFACTIQ/claude-remote-bridge.git
cd claude-remote-bridge
pip install requests
crb start my-topic
python3 src/install_hook.py
```

Then send messages from anywhere: `curl -d "hello" ntfy.sh/my-topic`

## Who Is This For?

Anyone running long Claude Code sessions:
- ML engineers training models overnight
- DevOps teams running deployment pipelines
- Developers with long build/test cycles
- Anyone who wants to monitor AI agent work from their phone

The tool is minimal by design - single Python dependency (`requests`), no databases, no authentication complexity. It uses local files for message queuing and ntfy.sh for transport.

## What's Next

We're exploring:
- WebSocket support for lower latency
- Message signing for authenticated environments
- Multi-session support (bridge multiple Claude instances)

If you're using Claude Code for long-running tasks, give it a try and let us know how it works for your workflow.

---

*ARTIFACTIQ builds AI-powered fashion recognition technology. We use Claude Code extensively for ML model training, data pipeline management, and infrastructure automation.*

*#ClaudeCode #AITools #MachineLearning #OpenSource #DeveloperTools #Anthropic #MLOps*
