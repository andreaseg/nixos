import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

KANJIAPI = "https://kanjiapi.dev/v1/kanji"
KANJI_CACHE_FILE = Path.home() / ".cache" / "jisho" / "kanji.json"


def _fetch_one(kanji: str) -> dict | None:
    resp = requests.get(f"{KANJIAPI}/{kanji}", timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _load_cache() -> dict[str, dict]:
    """Persistent char→data map. No TTL: KANJIDIC2 data is static."""
    if not KANJI_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(KANJI_CACHE_FILE.read_text())
    except (json.JSONDecodeError, KeyError):
        return {}


def _save_cache(data: dict[str, dict]) -> None:
    KANJI_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    KANJI_CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False))


def lookup_kanji_chars(chars: list[str]) -> dict[str, dict | None]:
    """Return kanjiapi data for each char, parallel + cached."""
    cache = _load_cache()
    to_fetch = [c for c in chars if c not in cache]

    if to_fetch:
        def _fetch(char: str) -> tuple[str, dict | None]:
            try:
                return char, _fetch_one(char)
            except requests.RequestException:
                return char, None

        with ThreadPoolExecutor(max_workers=len(to_fetch)) as ex:
            fetched = dict(ex.map(_fetch, to_fetch))

        updates = {c: d for c, d in fetched.items() if d is not None}
        if updates:
            _save_cache({**cache, **updates})
        cache.update(fetched)

    return {c: cache.get(c) for c in chars}
