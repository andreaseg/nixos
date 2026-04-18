import json
import os
import time
from pathlib import Path

import requests

from .utils import to_katakana

WANIKANI_TOKEN_FILE = Path.home() / ".config" / "wanikani" / "token"
WANIKANI_API = "https://api.wanikani.com/v2"
WK_CACHE_FILE = Path.home() / ".cache" / "jisho" / "wanikani.json"


def get_wanikani_token() -> str | None:
    token = os.environ.get("WANIKANI_API_TOKEN")
    if token:
        return token.strip()
    if WANIKANI_TOKEN_FILE.exists():
        return WANIKANI_TOKEN_FILE.read_text().strip()
    return None


def wk_fetch_pages(url: str, token: str) -> list[dict]:
    items: list[dict] = []
    next_url: str | None = url
    while next_url:
        resp = requests.get(
            next_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        items.extend(body["data"])
        next_url = body["pages"].get("next_url")
    return items


def wk_fetch_all(token: str) -> dict | None:
    try:
        subjects = wk_fetch_pages(
            f"{WANIKANI_API}/subjects?types=vocabulary,kanji", token,
        )
        assignments = wk_fetch_pages(
            f"{WANIKANI_API}/assignments?burned=true", token,
        )
        # Burned status lives on assignments, not subjects.
        burned_ids = {a["data"]["subject_id"] for a in assignments}

        vocabulary: dict[str, dict] = {}
        kanji: dict[str, dict] = {}

        for subject in subjects:
            data = subject["data"]
            slug = data["slug"]
            burned = subject["id"] in burned_ids
            meanings = [m["meaning"] for m in data.get("meanings", [])]
            readings = data.get("readings", [])

            if subject["object"] == "vocabulary":
                vocabulary[slug] = {
                    "level": data["level"],
                    "meanings": meanings,
                    "readings": [r["reading"] for r in readings],
                    "burned": burned,
                }
            else:
                kanji[slug] = {
                    "level": data["level"],
                    "meanings": meanings,
                    "on_readings": [
                        to_katakana(r["reading"])
                        for r in readings
                        if r.get("type") == "onyomi"
                    ],
                    "kun_readings": [
                        r["reading"]
                        for r in readings
                        if r.get("type") == "kunyomi"
                    ],
                    "burned": burned,
                }

        return {"vocabulary": vocabulary, "kanji": kanji}
    except (requests.RequestException, KeyError):
        return None


def wk_load_cache(ttl: int) -> tuple[dict, bool] | None:
    """Return (data, is_expired), or None if no cache file exists."""
    if not WK_CACHE_FILE.exists():
        return None
    try:
        raw = json.loads(WK_CACHE_FILE.read_text())
        expired = time.time() - raw["timestamp"] > ttl
        return raw["data"], expired
    except (json.JSONDecodeError, KeyError):
        return None


def wk_save_cache(data: dict) -> None:
    WK_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    WK_CACHE_FILE.write_text(json.dumps({
        "timestamp": time.time(),
        "data": data,
    }))


def get_wk_subjects(token: str | None, ttl: int) -> dict:
    empty = {"vocabulary": {}, "kanji": {}}

    if not token:
        result = wk_load_cache(ttl)
        return result[0] if result else empty

    cached = wk_load_cache(ttl)

    if cached and not cached[1]:
        return cached[0]

    fresh = wk_fetch_all(token)
    if fresh is not None:
        wk_save_cache(fresh)
        return fresh

    return cached[0] if cached else empty
