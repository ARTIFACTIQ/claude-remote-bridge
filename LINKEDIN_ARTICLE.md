We ran a 14-hour ML training job with Claude Code last week. 46 data shards, sequential YOLO fine-tuning on M4 Max.

The problem? You can't just walk away from an AI agent. Claude Code needed approvals, shards failed mid-run, and we wanted to check progress from our phone.

So we built Claude Remote Bridge - and open-sourced it.

---

The constraint: Claude Code can't be interrupted externally. No push notifications, no webhooks, no way to nudge it remotely.

The fix: A lightweight bridge daemon that uses ntfy.sh as a message bus.

Phone --> ntfy.sh --> Bridge Daemon --> Claude Code
Claude Code --> Bridge Daemon --> ntfy.sh --> Phone

It polls ntfy every 5 seconds, writes messages to a local inbox, and a Claude Code hook auto-checks it on every interaction.

---

The killer feature: built-in queries.

Send "q: training" from your phone. The bridge answers directly - no Claude interaction needed.

"Epoch 5/15 - 35% complete | Box: 2.3 | Cls: 1.9"

Also supports: disk space, running processes, log tails.

---

How our actual 14-hour run went:

Hour 3: "q: training" -> Shard 15/46, loss trending down
Hour 8: "q: logs" -> noticed early stopping on shard 21
Hour 12: notification -> "7 early-stopped shards, running weighted avg retry"
Hour 14: "E9 complete. mAP50=0.040, +22% over baseline. RELEASE."

We sent "approved" from our phone. Claude exported the model and tagged the release. Zero keyboard time after launch.

---

Setup takes 30 seconds:

git clone github.com/ARTIFACTIQ/claude-remote-bridge
pip install requests
crb start my-topic
python3 src/install_hook.py

Single dependency. No databases. Local files for queuing, ntfy.sh for transport.

---

Built for anyone running long Claude Code sessions - ML training, deployments, data pipelines, overnight builds.

Link in comments.

#ClaudeCode #OpenSource #MachineLearning #DeveloperTools #MLOps #AITools #Anthropic
