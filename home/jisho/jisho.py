import argparse
import json
import os
import sys
import time
import requests
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Protocol
from rich.cells import cell_len
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

# ── Constants ────────────────────────────────────────────────────────────────

# WaniKani
WANIKANI_TOKEN_FILE = Path.home() / ".config" / "wanikani" / "token"
WANIKANI_API = "https://api.wanikani.com/v2"
WK_CACHE_FILE = Path.home() / ".cache" / "jisho" / "wanikani.json"

# KanjiAPI — KANJIDIC2-backed, the same data source Jisho uses internally
KANJIAPI = "https://kanjiapi.dev/v1/kanji"

# AnkiConnect — local REST bridge bundled as an Anki add-on
ANKI_CONNECT = "http://localhost:8765"
ANKI_CACHE_FILE = Path.home() / ".cache" / "jisho" / "anki_words.json"

# Tool config — written by the Nix module at build time
JISHO_CONFIG_FILE = Path.home() / ".config" / "jisho" / "config.json"


# ── Config ───────────────────────────────────────────────────────────────────


@dataclass
class Colors:
    title: str = "default"
    badge_anki: str = "bold green"
    badge_wk: str = "bold magenta"
    badge_common: str = "green"
    badge_jlpt: str = "yellow"
    badge_warning: str = "yellow"
    badge_danger: str = "red"
    border_anki: str = "green"
    border_wk: str = "magenta"
    border_default: str = "blue"
    text_label: str = "italic dim"
    text_value: str = "default"
    text_reading: str = "cyan"


@dataclass
class Badges:
    anki: str = "★ Anki"
    wk_prefix: str = "⬡ WaniKani L"
    burned: str = " 🔥"
    common: str = "● common"
    jlpt_prefix: str = "● "
    not_in_wk: str = "⚠ not in WaniKani"
    not_jouyou: str = "⚠ not jouyou"


@dataclass
class Cache:
    wk_ttl: int = 604800     # WaniKani refresh threshold (7 days)
    anki_stale: int = 604800  # Anki stale-warning threshold (7 days)


@dataclass
class Config:
    colors: Colors
    badges: Badges
    anki_fields: dict[str, str]
    cache: Cache
    format: str = "rich"


def _parse_colors(raw: dict) -> Colors:
    defaults = Colors()
    badge = raw.get("badge", {})
    border = raw.get("border", {})
    text = raw.get("text", {})
    return Colors(
        title=raw.get("title", defaults.title),
        badge_anki=badge.get("anki", defaults.badge_anki),
        badge_wk=badge.get("wanikani", defaults.badge_wk),
        badge_common=badge.get("common", defaults.badge_common),
        badge_jlpt=badge.get("jlpt", defaults.badge_jlpt),
        badge_warning=badge.get(
            "warning", defaults.badge_warning
        ),
        badge_danger=badge.get("danger", defaults.badge_danger),
        border_anki=border.get("anki", defaults.border_anki),
        border_wk=border.get("wanikani", defaults.border_wk),
        border_default=border.get(
            "default", defaults.border_default
        ),
        text_label=text.get("label", defaults.text_label),
        text_value=text.get("value", defaults.text_value),
        text_reading=text.get("reading", defaults.text_reading),
    )


def _parse_badges(raw: dict) -> Badges:
    defaults = Badges()
    return Badges(
        anki=raw.get("anki", defaults.anki),
        wk_prefix=raw.get("wkPrefix", defaults.wk_prefix),
        burned=raw.get("burned", defaults.burned),
        common=raw.get("common", defaults.common),
        jlpt_prefix=raw.get("jlptPrefix", defaults.jlpt_prefix),
        not_in_wk=raw.get("notInWk", defaults.not_in_wk),
        not_jouyou=raw.get("notJouyou", defaults.not_jouyou),
    )


def _parse_cache(raw: dict) -> Cache:
    defaults = Cache()
    return Cache(
        wk_ttl=raw.get("wkTtl", defaults.wk_ttl),
        anki_stale=raw.get("ankiStaleTtl", defaults.anki_stale),
    )


def load_config() -> Config:
    fallback = Config(Colors(), Badges(), {}, Cache())
    if not JISHO_CONFIG_FILE.exists():
        return fallback
    try:
        raw = json.loads(JISHO_CONFIG_FILE.read_text())
        anki = raw.get("anki", {})
        return Config(
            colors=_parse_colors(raw.get("colors", {})),
            badges=_parse_badges(raw.get("badges", {})),
            anki_fields=anki.get("fields", {}),
            cache=_parse_cache(raw.get("cache", {})),
            format=raw.get("format", "rich"),
        )
    except (json.JSONDecodeError, KeyError):
        return fallback


# ── Domain model ─────────────────────────────────────────────────────────────


@dataclass
class VocabEntry:
    word: str
    reading: str
    is_common: bool
    jlpt: list[str]
    meanings: list[str]
    wk_level: int | None = None
    wk_burned: bool = False
    in_anki: bool = False


@dataclass
class KanjiEntry:
    character: str
    meanings: list[str]
    on_readings: list[str]
    kun_readings: list[str]
    is_jouyou: bool
    wk_level: int | None = None
    wk_burned: bool = False
    in_anki: bool = False

    @property
    def unknown(self) -> bool:
        return not self.in_anki and not self.wk_burned


@dataclass
class LookupResult:
    query: str
    vocabulary: list[VocabEntry]
    kanji: list[KanjiEntry]
    more_vocabulary: int = 0  # results beyond the display limit


# ── Utilities ────────────────────────────────────────────────────────────────


def to_katakana(text: str) -> str:
    # Hiragana (U+3041–U+3096) and katakana (U+30A1–U+30F6) share the
    # same glyph layout with a fixed offset of 0x60, so we can convert
    # by arithmetic rather than a lookup table.
    return "".join(
        chr(ord(c) + 0x60) if "\u3041" <= c <= "\u3096" else c
        for c in text
    )


def extract_kanji(text: str) -> list[str]:
    # dict.fromkeys preserves first-occurrence order while deduplicating,
    # which a plain set() does not guarantee.
    return list(
        dict.fromkeys(c for c in text if "\u4e00" <= c <= "\u9fff")
    )


def get_wanikani_token() -> str | None:
    token = os.environ.get("WANIKANI_API_TOKEN")
    if token:
        return token.strip()
    if WANIKANI_TOKEN_FILE.exists():
        return WANIKANI_TOKEN_FILE.read_text().strip()
    return None


# ── WaniKani ─────────────────────────────────────────────────────────────────


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
            f"{WANIKANI_API}/subjects?types=vocabulary,kanji",
            token,
        )
        assignments = wk_fetch_pages(
            f"{WANIKANI_API}/assignments?burned=true",
            token,
        )
        # Burned status lives on assignments, not subjects, requiring a
        # separate request. We only fetch burned=true to keep the payload
        # small — we display burn status but not SRS stage.
        burned_ids = {a["data"]["subject_id"] for a in assignments}

        # Vocabulary and kanji are keyed separately because the same slug
        # (e.g. "猫") can appear in both dicts. A shared dict would cause
        # one entry to silently overwrite the other.
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
        # No token — show whatever is cached rather than empty results.
        # This lets the tool work offline with the last known WK state.
        result = wk_load_cache(ttl)
        return result[0] if result else empty

    cached = wk_load_cache(ttl)

    if cached and not cached[1]:
        return cached[0]

    fresh = wk_fetch_all(token)
    if fresh is not None:
        wk_save_cache(fresh)
        return fresh

    # A fetch failure should not wipe out WaniKani enrichment — fall back
    # to whatever we last cached rather than silently returning nothing.
    return cached[0] if cached else empty


# ── Anki ─────────────────────────────────────────────────────────────────────


def anki_request(action: str, **params) -> object:
    payload = {"action": action, "version": 6, "params": params}
    resp = requests.post(ANKI_CONNECT, json=payload, timeout=3)
    resp.raise_for_status()
    result = resp.json()
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result["result"]


def anki_fetch_words(fields: dict[str, str]) -> set[str] | None:
    try:
        words: set[str] = set()
        for note_type, field_name in fields.items():
            note_ids = anki_request(
                "findNotes", query=f'note:"{note_type}"'
            )
            if not note_ids:
                continue
            notes = anki_request("notesInfo", notes=list(note_ids))
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


def anki_load_cache(stale: int) -> tuple[set[str], bool] | None:
    """Return (words, is_stale) or None if no cache file."""
    if not ANKI_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(ANKI_CACHE_FILE.read_text())
        age = time.time() - data["timestamp"]
        return set(data["words"]), age > stale
    except (json.JSONDecodeError, KeyError):
        return None


def anki_save_cache(words: set[str]) -> None:
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
    live = anki_fetch_words(fields)
    if live is not None:
        anki_save_cache(live)
        return live, []
    if not fields:
        return set(), []
    cached = anki_load_cache(stale)
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


# ── API calls ────────────────────────────────────────────────────────────────


def search_jisho(query: str) -> list[dict]:
    resp = requests.get(
        "https://jisho.org/api/v1/search/words",
        params={"keyword": query},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def lookup_kanji_data(kanji: str) -> dict | None:
    resp = requests.get(f"{KANJIAPI}/{kanji}", timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


# ── Parsing ──────────────────────────────────────────────────────────────────


def is_exact_match(raw: dict, query: str) -> bool:
    for j in raw.get("japanese", []):
        if j.get("word") == query or j.get("reading") == query:
            return True
    return False


def parse_vocab_entry(
    raw: dict,
    wk_subject: dict | None,
    in_anki: bool = False,
) -> VocabEntry:
    japanese = raw.get("japanese", [{}])
    word = japanese[0].get("word", "")
    reading = japanese[0].get("reading", "")

    if wk_subject:
        wk_readings = wk_subject["readings"]
        # Prefer WaniKani's reading: WK teaches one canonical reading,
        # while Jisho may surface a different (also valid) reading first.
        if wk_readings:
            reading = wk_readings[0]
        return VocabEntry(
            word=word,
            reading=reading,
            is_common=raw.get("is_common", False),
            jlpt=raw.get("jlpt", []),
            meanings=wk_subject["meanings"],
            wk_level=wk_subject["level"],
            wk_burned=wk_subject["burned"],
            in_anki=in_anki,
        )

    all_defs = [
        d
        for s in raw.get("senses", [])
        for d in s.get("english_definitions", [])
    ]
    return VocabEntry(
        word=word,
        reading=reading,
        is_common=raw.get("is_common", False),
        jlpt=raw.get("jlpt", []),
        meanings=all_defs,
        in_anki=in_anki,
    )


def parse_kanji_entry(
    kanji: str,
    wk_subject: dict | None,
    kanji_data: dict | None,
    in_anki: bool = False,
) -> KanjiEntry:
    # jouyou grade comes from kanjiapi regardless of which source we use
    # for meanings/readings, so compute it up front.
    is_jouyou = (
        kanji_data is not None and kanji_data.get("grade") is not None
    )

    if wk_subject:
        return KanjiEntry(
            character=kanji,
            meanings=wk_subject["meanings"],
            on_readings=wk_subject["on_readings"],
            kun_readings=wk_subject["kun_readings"],
            is_jouyou=is_jouyou,
            wk_level=wk_subject["level"],
            wk_burned=wk_subject["burned"],
            in_anki=in_anki,
        )

    if kanji_data:
        return KanjiEntry(
            character=kanji,
            meanings=kanji_data.get("meanings", []),
            # kanjiapi returns on-readings in hiragana; convert to
            # katakana to match convention (and WaniKani's format).
            on_readings=[
                to_katakana(r)
                for r in kanji_data.get("on_readings", [])
            ],
            kun_readings=kanji_data.get("kun_readings", []),
            is_jouyou=is_jouyou,
            in_anki=in_anki,
        )

    return KanjiEntry(
        character=kanji,
        meanings=[],
        on_readings=[],
        kun_readings=[],
        is_jouyou=False,
        in_anki=in_anki,
    )


# ── Lookup ───────────────────────────────────────────────────────────────────


def lookup(
    query: str,
    wk_subjects: dict,
    anki_words: set[str],
    limit: int = 5,
) -> LookupResult:
    """Fetch and parse all data for a query. Raises on Jisho failure."""
    results = search_jisho(query)

    if not results:
        return LookupResult(query=query, vocabulary=[], kanji=[])

    exact = [r for r in results if is_exact_match(r, query)]

    # When the query has an exact match, show only those entries.
    # Without this filter, Jisho returns loosely related results that
    # would flood the output for common words.
    pool = exact if exact else results
    to_show = pool[:limit]
    more = len(pool) - len(to_show)

    vocabulary: list[VocabEntry] = []
    for raw in to_show:
        first = raw.get("japanese", [{}])[0]
        reading = first.get("reading", "")
        word = first.get("word", "")

        # Match by the result's own word/reading, not the query — so
        # searching by reading (ねこ) or meaning (cat) still enriches
        # correctly when the result's word (猫) is in Anki or WaniKani.
        entry_in_anki = word in anki_words or reading in anki_words

        # Verify reading before accepting the WK match — the same written
        # form can have multiple readings (e.g. 上手 as じょうず vs うまい).
        wk = wk_subjects["vocabulary"].get(word)
        if wk and reading not in wk["readings"]:
            wk = None

        vocabulary.append(parse_vocab_entry(
            raw, wk, in_anki=entry_in_anki,
        ))

    kanji_chars = extract_kanji(query)
    wk_kanji = {
        k: wk_subjects["kanji"][k]
        for k in kanji_chars
        if k in wk_subjects["kanji"]
    }

    kanji: list[KanjiEntry] = []
    for char in kanji_chars:
        try:
            kanji_data = lookup_kanji_data(char)
        except requests.RequestException:
            kanji_data = None
        # Mark a kanji as known if it appears in any Anki word, not just
        # as a standalone card — knowing 猫缶 implies exposure to 猫.
        char_in_anki = any(char in word for word in anki_words)
        kanji.append(parse_kanji_entry(
            char, wk_kanji.get(char), kanji_data,
            in_anki=char_in_anki,
        ))

    return LookupResult(
        query=query,
        vocabulary=vocabulary,
        kanji=kanji,
        more_vocabulary=more,
    )


# ── Output strategies ────────────────────────────────────────────────────────


class Formatter(Protocol):
    def output(self, result: LookupResult) -> None: ...


class RichFormatter:
    def __init__(
        self,
        console: Console,
        colors: Colors,
        badges: Badges,
        verbose: bool = False,
    ) -> None:
        self.console = console
        self.colors = colors
        self.badges = badges
        self.verbose = verbose

    def output(self, result: LookupResult) -> None:
        for entry in result.vocabulary:
            self._render_vocab(entry)
            self.console.print()

        if result.more_vocabulary:
            self.console.print(
                f"  [dim]… {result.more_vocabulary} more result"
                f"{'s' if result.more_vocabulary > 1 else ''}"
                " — use --limit to show more[/dim]"
            )
            self.console.print()

        kanji = (
            result.kanji if self.verbose
            else [k for k in result.kanji if k.unknown]
        )
        if kanji:
            title = "Kanji" if self.verbose else "Unknown Kanji"
            self.console.print(
                Rule(f"[dim]{title}[/dim]", style="dim")
            )
            self.console.print()
            for entry in kanji:
                self._render_kanji(entry)
                self.console.print()

    def _wk_badge_text(self, level: int, burned: bool) -> str:
        text = f"{self.badges.wk_prefix}{level}"
        if burned:
            text += self.badges.burned
        return text

    def _render_vocab(self, entry: VocabEntry) -> None:
        c = self.colors
        b = self.badges
        title = Text()
        title.append(entry.word or entry.reading, style=c.title)

        badges = Text()
        if entry.in_anki:
            badges.append(b.anki, style=c.badge_anki)
            badges.append("  ")
        if entry.wk_level is not None:
            badges.append(
                self._wk_badge_text(entry.wk_level, entry.wk_burned),
                style=c.badge_wk,
            )
            badges.append("  ")
        if entry.is_common:
            badges.append(b.common, style=c.badge_common)
        if entry.jlpt:
            if entry.is_common:
                badges.append("  ")
            jlpt_str = entry.jlpt[0].replace("jlpt-", "").upper()
            badges.append(
                f"{b.jlpt_prefix}{jlpt_str}", style=c.badge_jlpt
            )

        body = Text()
        body.append("  Readings: ", style=c.text_label)
        body.append(entry.reading + "\n", style=c.text_value)
        body.append("  Meanings: ", style=c.text_label)
        body.append(
            ", ".join(entry.meanings) + "\n", style=c.text_value
        )

        # Border colour reflects data source priority: Anki > WK > default
        border = c.border_anki if entry.in_anki else (
            c.border_wk if entry.wk_level is not None
            else c.border_default
        )
        content = Text.assemble(badges, "\n\n", body) if badges else body
        self.console.print(Panel(
            content,
            title=title,
            title_align="left",
            border_style=border,
            padding=(0, 1),
        ))

    def _render_kanji(self, entry: KanjiEntry) -> None:
        c = self.colors
        b = self.badges
        title = Text(entry.character, style=c.title)

        badges = Text()
        if entry.in_anki:
            badges.append(b.anki, style=c.badge_anki)
            badges.append("  ")
        if entry.wk_level is not None:
            badges.append(
                self._wk_badge_text(entry.wk_level, entry.wk_burned),
                style=c.badge_wk,
            )
        else:
            badges.append(b.not_in_wk, style=c.badge_warning)
        if not entry.is_jouyou:
            badges.append("  ")
            badges.append(b.not_jouyou, style=c.badge_danger)

        body = Text()
        if entry.meanings or entry.on_readings or entry.kun_readings:
            if entry.meanings:
                body.append("  Meanings: ", style=c.text_label)
                body.append(
                    ", ".join(entry.meanings) + "\n",
                    style=c.text_value,
                )
            if entry.on_readings:
                body.append("  On: ", style=c.text_label)
                body.append(
                    ", ".join(entry.on_readings) + "\n",
                    style=c.text_value,
                )
            if entry.kun_readings:
                body.append("  Kun: ", style=c.text_label)
                body.append(
                    ", ".join(entry.kun_readings) + "\n",
                    style=c.text_value,
                )
        else:
            body.append("  No data found\n", style="dim")

        content = Text.assemble(badges, "\n\n", body) if badges else body
        self.console.print(Panel(
            content,
            title=title,
            title_align="left",
            border_style=(
                c.border_wk if entry.wk_level is not None
                else c.border_default
            ),
            padding=(0, 1),
        ))


class CompactFormatter:
    """One line per entry: {word} {reading} {meanings} {badges}."""

    def __init__(
        self,
        console: Console,
        colors: Colors,
        badges: Badges,
        verbose: bool = False,
    ) -> None:
        self.console = console
        self.colors = colors
        self.badges = badges
        self.verbose = verbose

    def _col_width(self, values: list[str]) -> int:
        """80th-percentile display width — caps outliers without truncating."""
        if not values:
            return 0
        widths = sorted(cell_len(v) for v in values)
        return widths[int(len(widths) * 0.8)]

    def output(self, result: LookupResult) -> None:
        # Pre-compute column widths so entries align without one long
        # outlier inflating the padding for every other line.
        word_w = self._col_width(
            [e.word or e.reading for e in result.vocabulary]
        )
        read_w = self._col_width(
            [e.reading for e in result.vocabulary if e.word]
        )
        for entry in result.vocabulary:
            self._render_vocab(entry, word_w, read_w)

        if result.more_vocabulary:
            self.console.print(
                f"[dim]… {result.more_vocabulary} more result"
                f"{'s' if result.more_vocabulary > 1 else ''}"
                " — use --limit to show more[/dim]"
            )

        kanji = (
            result.kanji if self.verbose
            else [k for k in result.kanji if k.unknown]
        )
        if kanji:
            self.console.print("[dim]── Kanji ──[/dim]")
            for entry in kanji:
                self._render_kanji(entry)

    def _render_vocab(
        self,
        entry: VocabEntry,
        word_w: int = 0,
        read_w: int = 0,
    ) -> None:
        c = self.colors
        line = Text()
        word = entry.word or entry.reading
        w = cell_len(word)
        line.append(word, style=c.title)
        if entry.word:
            # Pad each column separately; outliers get one space
            line.append(" " * max(1, word_w - w + 1))
            r = cell_len(entry.reading)
            line.append(entry.reading, style=c.text_reading)
            line.append(" " * max(1, read_w - r + 1))
        else:
            # No reading — pad both columns together so the meaning
            # column stays aligned even when the word overflows word_w
            line.append(
                " " * max(1, word_w + read_w + 2 - w)
            )
        line.append(", ".join(entry.meanings), style=c.text_value)
        if entry.in_anki:
            line.append("  A", style=c.badge_anki)
        if entry.wk_level is not None:
            wk = f"  🐢{entry.wk_level}"
            if entry.wk_burned:
                wk += "🔥"
            line.append(wk, style=c.badge_wk)
        if entry.is_common:
            line.append("  C", style=c.badge_common)
        if entry.jlpt:
            jlpt_str = entry.jlpt[0].replace("jlpt-", "").upper()
            line.append(f"  {jlpt_str}", style=c.badge_jlpt)
        self.console.print(line)

    def _render_kanji(self, entry: KanjiEntry) -> None:
        c = self.colors
        line = Text()
        line.append(entry.character, style=c.title)
        readings = ", ".join(entry.on_readings + entry.kun_readings)
        if readings:
            line.append(f" {readings}", style=c.text_reading)
        if entry.meanings:
            line.append(
                f" {', '.join(entry.meanings)}", style=c.text_value
            )
        if entry.in_anki:
            line.append("  A", style=c.badge_anki)
        if entry.wk_level is not None:
            wk = f"  🐢{entry.wk_level}"
            if entry.wk_burned:
                wk += "🔥"
            line.append(wk, style=c.badge_wk)
        else:
            line.append("  ∅🐢", style=c.badge_warning)
        if not entry.is_jouyou:
            line.append("  ∅J", style=c.badge_danger)
        self.console.print(line)


class JsonFormatter:
    def output(self, result: LookupResult) -> None:
        data = asdict(result)
        print(json.dumps(data, ensure_ascii=False, indent=2))


# ── Init-config command ──────────────────────────────────────────────────────


def is_nix_managed(path: Path) -> bool:
    # home-manager writes config files as symlinks into /nix/store/
    return path.is_symlink() and "/nix/store/" in str(path.resolve())


def default_config_dict() -> dict:
    """Default config as a dict matching the JSON structure."""
    c = Colors()
    b = Badges()
    ca = Cache()
    return {
        "format": "rich",
        "colors": {
            "title": c.title,
            "badge": {
                "anki": c.badge_anki,
                "wanikani": c.badge_wk,
                "common": c.badge_common,
                "jlpt": c.badge_jlpt,
                "warning": c.badge_warning,
                "danger": c.badge_danger,
            },
            "border": {
                "anki": c.border_anki,
                "wanikani": c.border_wk,
                "default": c.border_default,
            },
            "text": {
                "label": c.text_label,
                "value": c.text_value,
                "reading": c.text_reading,
            },
        },
        "badges": {
            "anki": b.anki,
            "wkPrefix": b.wk_prefix,
            "burned": b.burned,
            "common": b.common,
            "jlptPrefix": b.jlpt_prefix,
            "notInWk": b.not_in_wk,
            "notJouyou": b.not_jouyou,
        },
        "anki": {"fields": {}},
        "cache": {
            "wkTtl": ca.wk_ttl,
            "ankiStaleTtl": ca.anki_stale,
        },
    }


def cmd_init_config(force: bool) -> None:
    if is_nix_managed(JISHO_CONFIG_FILE):
        print(
            "error: config is managed by Nix home-manager —"
            " edit programs.jisho in your Nix config instead.",
            file=sys.stderr,
        )
        sys.exit(1)
    if JISHO_CONFIG_FILE.exists() and not force:
        print(
            f"error: config already exists at {JISHO_CONFIG_FILE}"
            " — use --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)
    JISHO_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    JISHO_CONFIG_FILE.write_text(
        json.dumps(default_config_dict(), ensure_ascii=False, indent=2)
    )
    print(f"Config written to {JISHO_CONFIG_FILE}")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "init-config":
        force = "--force" in sys.argv[2:]
        cmd_init_config(force)
        return

    config = load_config()
    parser = argparse.ArgumentParser(
        prog="jisho",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Japanese dictionary lookup powered by jisho.org\n"
            "\n"
            "Looks up Japanese words and kanji with optional enrichment\n"
            "from WaniKani and Anki. Results show readings, meanings,\n"
            "JLPT level, and your learning status across both tools."
        ),
        epilog=(
            "wanikani integration:\n"
            "  Set WANIKANI_API_TOKEN or write your token to\n"
            "  ~/.config/wanikani/token. Subject data is cached locally\n"
            "  (see --help for cache TTL config).\n"
            "\n"
            "anki integration:\n"
            "  Requires the AnkiConnect add-on running inside Anki.\n"
            "  Configure note type → field mappings in your config file.\n"
            "\n"
            "subcommands:\n"
            "  init-config [--force]\n"
            "      Write a default config to "
            "~/.config/jisho/config.json\n"
            "      for easy editing. Aborts if the file is managed by\n"
            "      Nix home-manager. Use --force to overwrite an\n"
            "      existing unmanaged config.\n"
            "\n"
            "examples:\n"
            "  jisho 猫\n"
            "  jisho 日本語 --format compact\n"
            "  jisho 勉強 --verbose --limit 10\n"
            "  jisho init-config"
        ),
    )
    parser.add_argument("query", nargs="+", help="Word to look up")
    parser.add_argument(
        "--format", default=config.format,
        choices=["rich", "compact", "json"],
        help="Output format (default: rich)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show all kanji, not just unknown ones",
    )
    parser.add_argument(
        "--limit", type=int, default=5, metavar="N",
        help="Maximum vocabulary results to show (default: 5)",
    )
    args = parser.parse_args()

    query = " ".join(args.query)
    token = get_wanikani_token()
    wk_subjects = get_wk_subjects(token, config.cache.wk_ttl)
    anki_words, anki_warnings = get_anki_words(
        config.anki_fields, config.cache.anki_stale
    )
    if anki_warnings:
        warn = Console(stderr=True, force_terminal=True)
        for w in anki_warnings:
            warn.print(f"[yellow]Warning:[/yellow] {w}")

    try:
        result = lookup(
            query, wk_subjects, anki_words, limit=args.limit
        )
    except requests.RequestException as e:
        if args.format == "json":
            print(json.dumps({"error": str(e)}))
        else:
            Console(force_terminal=True).print(
                f"[red]Request failed:[/red] {e}"
            )
        sys.exit(1)

    if not result.vocabulary and not result.kanji:
        if args.format == "json":
            print(json.dumps(asdict(result), ensure_ascii=False))
        else:
            Console(force_terminal=True).print(
                f"[yellow]No results for '{query}'[/yellow]"
            )
        sys.exit(0)

    formatter: Formatter
    if args.format == "json":
        formatter = JsonFormatter()
    elif args.format == "compact":
        formatter = CompactFormatter(
            Console(force_terminal=True),
            config.colors,
            config.badges,
            verbose=args.verbose,
        )
    else:
        formatter = RichFormatter(
            Console(force_terminal=True),
            config.colors,
            config.badges,
            verbose=args.verbose,
        )

    formatter.output(result)


if __name__ == "__main__":
    main()
