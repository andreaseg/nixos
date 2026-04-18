import json
import time
from pathlib import Path

import requests

ANKI_CONNECT = "http://localhost:8765"
ANKI_CACHE_FILE = Path.home() / ".cache" / "jisho" / "anki_words.json"


def _request(action: str, **params) -> object:
    payload = {"action": action, "version": 6, "params": params}
    resp = requests.post(ANKI_CONNECT, json=payload, timeout=3)
    resp.raise_for_status()
    result = resp.json()
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result["result"]


def _fetch_words(fields: dict[str, str]) -> set[str] | None:
    try:
        words: set[str] = set()
        for note_type, field_name in fields.items():
            note_ids = _request("findNotes", query=f'note:"{note_type}"')
            if not note_ids:
                continue
            notes = _request("notesInfo", notes=list(note_ids))
            for note in notes:
                value = (
                    note["fields"]
                    .get(field_name, {})
                    .get("value", "")
                    .strip()
                )
                if value:
                    words.add(value)
        return words
    except (requests.RequestException, RuntimeError, KeyError):
        return None


def _load_cache(stale: int) -> tuple[set[str], bool] | None:
    """Return (words, is_stale) or None if no cache file."""
    if not ANKI_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(ANKI_CACHE_FILE.read_text())
        age = time.time() - data["timestamp"]
        return set(data["words"]), age > stale
    except (json.JSONDecodeError, KeyError):
        return None


def _save_cache(words: set[str]) -> None:
    ANKI_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ANKI_CACHE_FILE.write_text(json.dumps({
        "timestamp": time.time(),
        "words": list(words),
    }))


def get_anki_words(
    fields: dict[str, str],
    stale: int,
) -> tuple[set[str], list[str]]:
    """Return (words, warnings)."""
    live = _fetch_words(fields)
    if live is not None:
        _save_cache(live)
        return live, []
    if not fields:
        return set(), []
    cached = _load_cache(stale)
    if cached is None:
        return set(), [
            "Anki is not running and no cache exists —"
            " start Anki to populate the cache."
        ]
    words, is_stale = cached
    if is_stale:
        stale_days = stale // 86400
        return words, [
            f"Anki cache is stale (>{stale_days}d) —"
            " start Anki to refresh it."
        ]
    return words, []
