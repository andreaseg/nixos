import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

HISTORY_FILE = Path.home() / ".bash_history"
MODEL = "claude-haiku-4-5"
MAX_COMMANDS = 300


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    if not HISTORY_FILE.exists():
        print("Error: ~/.bash_history not found", file=sys.stderr)
        sys.exit(1)

    lines = HISTORY_FILE.read_text(errors="ignore").splitlines()

    # Deduplicate, preserving order, keeping most recent occurrences
    seen: set[str] = set()
    unique: list[str] = []
    for line in reversed(lines):
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            unique.append(line)
    history_text = "\n".join(reversed(unique[:MAX_COMMANDS]))

    payload = {
        "model": MODEL,
        "max_tokens": 200,
        "messages": [{
            "role": "user",
            "content": (
                f"Here is my recent bash history:\n\n{history_text}\n\n"
                "Based on what I actually use, give me one specific tip to use "
                "my terminal more efficiently. Two sentences max."
            ),
        }],
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print(result["content"][0]["text"])
    except urllib.error.HTTPError as e:
        print(f"API error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


main()
