#!/usr/bin/env python3
"""
Query Handler for Claude Remote Bridge

Processes incoming queries and returns results.
Queries are messages starting with "query:" or "q:"

Supported queries:
    query: training     - Current training status
    query: tasks        - List all tasks
    query: disk         - Disk space usage
    query: processes    - Running Python/training processes
    query: logs [n]     - Last n lines of training log (default: 10)
    query: help         - List available queries

Usage:
    result = handle_query("query: training")
    # Returns: {"response": "...", "title": "Training Status", "tags": "..."}
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional


# Training log location (configurable via env)
TRAINING_LOG = os.environ.get("TRAINING_LOG", "/tmp/training.log")

# Process name pattern to search for (configurable via env)
TRAINING_PROCESS = os.environ.get("TRAINING_PROCESS", "train")

# Monitor process name pattern (configurable via env)
MONITOR_PROCESS = os.environ.get("MONITOR_PROCESS", "training_monitor")


def handle_query(message: str) -> Optional[Dict]:
    """
    Parse and handle a query message.

    Args:
        message: The incoming message text

    Returns:
        Dict with 'response', 'title', 'tags' keys, or None if not a query
    """
    # Check if this is a query
    message = message.strip()
    query_match = re.match(r'^(?:query|q):\s*(.+)$', message, re.IGNORECASE)

    if not query_match:
        return None

    query = query_match.group(1).strip().lower()

    # Route to appropriate handler
    handlers = {
        'training': query_training,
        'train': query_training,
        'status': query_training,
        'tasks': query_tasks,
        'task': query_tasks,
        'task list': query_tasks,
        'disk': query_disk,
        'space': query_disk,
        'processes': query_processes,
        'process': query_processes,
        'ps': query_processes,
        'logs': lambda: query_logs(10),
        'log': lambda: query_logs(10),
        'help': query_help,
        '?': query_help,
    }

    # Check for logs with number (e.g., "logs 20")
    logs_match = re.match(r'^logs?\s+(\d+)$', query)
    if logs_match:
        return query_logs(int(logs_match.group(1)))

    # Find and execute handler
    handler = handlers.get(query)
    if handler:
        return handler()

    # Unknown query
    return {
        "response": f"Unknown query: {query}\n\nUse 'query: help' for available commands.",
        "title": "Query Error",
        "tags": "x"
    }


def query_training() -> Dict:
    """Get current training status."""
    try:
        # Check if training process is running
        result = subprocess.run(
            ["pgrep", "-f", TRAINING_PROCESS],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            return {
                "response": "No training process running.",
                "title": "Training Status",
                "tags": "stop_sign"
            }

        pid = result.stdout.strip().split('\n')[0]

        # Get latest log line
        log_path = Path(TRAINING_LOG)
        if log_path.exists():
            # Read last line (may have \r for progress)
            with open(log_path, 'rb') as f:
                f.seek(0, 2)  # End of file
                size = f.tell()
                f.seek(max(0, size - 2000))  # Last 2KB
                content = f.read().decode('utf-8', errors='ignore')

            # Get last progress line
            lines = content.replace('\r', '\n').split('\n')
            progress_line = ""
            for line in reversed(lines):
                if re.search(r'\d+/\d+', line) and ('box_loss' in line.lower() or 'epoch' in line.lower() or '%' in line):
                    progress_line = line.strip()
                    break
                if re.search(r'\d+/\d+.*\d+%', line):
                    progress_line = line.strip()
                    break

            if progress_line:
                # Parse progress
                # Format: 1/N 1.7G 2.989 5.435 4.506 8 448: 78% ...
                match = re.search(r'(\d+)/(\d+).*?(\d+)%', progress_line)
                if match:
                    epoch, total_epochs, pct = match.groups()

                    # Extract losses
                    loss_match = re.search(r'(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)', progress_line)
                    losses = ""
                    if loss_match:
                        box, cls, dfl = loss_match.groups()
                        losses = f"\nBox: {box} | Cls: {cls} | DFL: {dfl}"

                    return {
                        "response": f"Epoch {epoch}/{total_epochs} - {pct}% complete{losses}\nPID: {pid}",
                        "title": "Training Status",
                        "tags": "chart_with_upwards_trend"
                    }

            return {
                "response": f"Training running (PID: {pid})\nUnable to parse progress.",
                "title": "Training Status",
                "tags": "hourglass"
            }

        return {
            "response": f"Training running (PID: {pid})\nNo log file found.",
            "title": "Training Status",
            "tags": "hourglass"
        }

    except Exception as e:
        return {
            "response": f"Error checking training: {str(e)[:100]}",
            "title": "Query Error",
            "tags": "x"
        }


def query_tasks() -> Dict:
    """Get task list status."""
    try:
        # Try to read from Claude's task system via the conversation
        # For now, check if there's a tasks file or use a simple approach

        # Check training status as primary task
        training_status = query_training()

        tasks = []

        # Training task
        if "No training" in training_status["response"]:
            tasks.append("1. [STOPPED] Training")
        else:
            match = re.search(r'Epoch (\d+)/(\d+).*?(\d+)%', training_status["response"])
            if match:
                epoch, total, pct = match.groups()
                tasks.append(f"1. [IN PROGRESS] Training - Epoch {epoch}/{total} ({pct}%)")
            else:
                tasks.append("1. [IN PROGRESS] Training")

        # Check for monitoring
        result = subprocess.run(
            ["pgrep", "-f", MONITOR_PROCESS],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            tasks.append("2. [RUNNING] Training Monitor (ntfy every 10m)")
        else:
            tasks.append("2. [STOPPED] Training Monitor")

        # Check bridge
        result = subprocess.run(
            ["pgrep", "-f", "bridge.py"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            tasks.append("3. [RUNNING] Claude Remote Bridge")
        else:
            tasks.append("3. [STOPPED] Claude Remote Bridge")

        return {
            "response": "\n".join(tasks),
            "title": "Task Status",
            "tags": "clipboard"
        }

    except Exception as e:
        return {
            "response": f"Error getting tasks: {str(e)[:100]}",
            "title": "Query Error",
            "tags": "x"
        }


def query_disk() -> Dict:
    """Get disk space usage."""
    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True, text=True
        )

        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                size, used, avail, pct = parts[1], parts[2], parts[3], parts[4]
                return {
                    "response": f"Used: {used}/{size} ({pct})\nAvailable: {avail}",
                    "title": "Disk Space",
                    "tags": "floppy_disk"
                }

        return {
            "response": result.stdout[:200],
            "title": "Disk Space",
            "tags": "floppy_disk"
        }

    except Exception as e:
        return {
            "response": f"Error: {str(e)[:100]}",
            "title": "Query Error",
            "tags": "x"
        }


def query_processes() -> Dict:
    """Get running Python/training processes."""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True
        )

        processes = []
        for line in result.stdout.split('\n'):
            if 'python' in line.lower() and ('train' in line.lower() or 'bridge' in line.lower() or 'yolo' in line.lower()):
                parts = line.split()
                if len(parts) >= 11:
                    pid = parts[1]
                    cpu = parts[2]
                    mem = parts[3]
                    cmd = ' '.join(parts[10:])[:40]
                    processes.append(f"PID {pid}: {cmd}... (CPU:{cpu}% MEM:{mem}%)")

        if processes:
            return {
                "response": "\n".join(processes[:5]),  # Max 5
                "title": "Processes",
                "tags": "gear"
            }

        return {
            "response": "No training/bridge processes found.",
            "title": "Processes",
            "tags": "gear"
        }

    except Exception as e:
        return {
            "response": f"Error: {str(e)[:100]}",
            "title": "Query Error",
            "tags": "x"
        }


def query_logs(n: int = 10) -> Dict:
    """Get last n lines of training log."""
    try:
        log_path = Path(TRAINING_LOG)
        if not log_path.exists():
            return {
                "response": "Training log not found.",
                "title": "Training Logs",
                "tags": "page_facing_up"
            }

        result = subprocess.run(
            ["tail", "-n", str(n), str(log_path)],
            capture_output=True, text=True
        )

        # Clean up ANSI codes and \r
        output = result.stdout
        output = re.sub(r'\x1b\[[0-9;]*m', '', output)  # Remove ANSI
        output = output.replace('\r', '\n')

        # Get meaningful lines
        lines = [l.strip() for l in output.split('\n') if l.strip()]
        lines = lines[-n:]

        return {
            "response": "\n".join(lines)[:500],  # Max 500 chars
            "title": f"Last {n} Log Lines",
            "tags": "page_facing_up"
        }

    except Exception as e:
        return {
            "response": f"Error: {str(e)[:100]}",
            "title": "Query Error",
            "tags": "x"
        }


def query_help() -> Dict:
    """List available queries."""
    help_text = """Available queries:
- training / status: Training progress
- tasks: List all tasks
- disk: Disk space usage
- processes / ps: Running processes
- logs [n]: Last n log lines
- help: This message

Example: query: training"""

    return {
        "response": help_text,
        "title": "Query Help",
        "tags": "question"
    }


if __name__ == "__main__":
    # Test queries
    import sys
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        result = handle_query(f"query: {query}")
        if result:
            print(f"Title: {result['title']}")
            print(f"Tags: {result['tags']}")
            print(f"Response:\n{result['response']}")
        else:
            print("Not a query")
    else:
        print("Usage: python query_handler.py <query>")
        print("Example: python query_handler.py training")
