import argparse
import json
import os
import sys
import time
import requests
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Protocol
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

WANIKANI_TOKEN_FILE = Path.home() / ".config" / "wanikani" / "token"
WANIKANI_API = "https://api.wanikani.com/v2"
WK_CACHE_FILE = Path.home() / ".cache" / "jisho" / "wanikani.json"
WK_CACHE_TTL = 604800  # 7 days in seconds

KANJIAPI = "https://kanjiapi.dev/v1/kanji"
JISHO_CONFIG_FILE = (
    Path.home() / ".config" / "jisho" / "config.json"
)

ANKI_CONNECT = "http://localhost:8765"
ANKI_CACHE_FILE = Path.home() / ".cache" / "jisho" / "anki_words.json"
ANKI_CACHE_TTL = 86400  # 1 day in seconds

DEFAULT_ANKI_FIELDS: dict[str, str] = {}


# ── Colors ───────────────────────────────────────────────────────────────────


@dataclass
class Colors:
    title: str = "bold cyan"
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
    text_value: str = "white"


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
class Config:
    colors: Colors
    badges: Badges
    anki_fields: dict[str, str]


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


def load_config() -> Config:
    fallback = Config(Colors(), Badges(), dict(DEFAULT_ANKI_FIELDS))
    if not JISHO_CONFIG_FILE.exists():
        return fallback
    try:
        raw = json.loads(JISHO_CONFIG_FILE.read_text())
        anki = raw.get("anki", {})
        return Config(
            colors=_parse_colors(raw.get("colors", {})),
            badges=_parse_badges(raw.get("badges", {})),
            anki_fields=anki.get(
                "fields", dict(DEFAULT_ANKI_FIELDS)
            ),
        )
    except (json.JSONDecodeError, KeyError):
        return fallback


# ── Dataclasses ──────────────────────────────────────────────────────────────


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


# ── Utilities ────────────────────────────────────────────────────────────────


def to_katakana(text: str) -> str:
    return "".join(
        chr(ord(c) + 0x60) if "\u3041" <= c <= "\u3096" else c
        for c in text
    )


def extract_kanji(text: str) -> list[str]:
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


# ── WaniKani cache ───────────────────────────────────────────────────────────


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


def wk_load_cache() -> tuple[dict, bool] | None:
    """Return (data, is_expired), or None if no cache file exists."""
    if not WK_CACHE_FILE.exists():
        return None
    try:
        raw = json.loads(WK_CACHE_FILE.read_text())
        expired = time.time() - raw["timestamp"] > WK_CACHE_TTL
        return raw["data"], expired
    except (json.JSONDecodeError, KeyError):
        return None


def wk_save_cache(data: dict) -> None:
    WK_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    WK_CACHE_FILE.write_text(json.dumps({
        "timestamp": time.time(),
        "data": data,
    }))


def get_wk_subjects(token: str | None) -> dict:
    """Return cached WaniKani subjects, refreshing when possible."""
    empty = {"vocabulary": {}, "kanji": {}}
    if not token:
        result = wk_load_cache()
        return result[0] if result else empty

    cached = wk_load_cache()

    if cached and not cached[1]:
        return cached[0]

    fresh = wk_fetch_all(token)
    if fresh is not None:
        wk_save_cache(fresh)
        return fresh

    # Fetch failed — fall back to stale cache rather than losing data
    return cached[0] if cached else empty


# ── Anki cache ───────────────────────────────────────────────────────────────


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


def anki_load_cache() -> set[str] | None:
    if not ANKI_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(ANKI_CACHE_FILE.read_text())
        if time.time() - data["timestamp"] > ANKI_CACHE_TTL:
            return None
        return set(data["words"])
    except (json.JSONDecodeError, KeyError):
        return None


def anki_save_cache(words: set[str]) -> None:
    ANKI_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ANKI_CACHE_FILE.write_text(json.dumps({
        "timestamp": time.time(),
        "words": list(words),
    }))


def get_anki_words(fields: dict[str, str]) -> set[str]:
    live = anki_fetch_words(fields)
    if live is not None:
        anki_save_cache(live)
        return live
    cached = anki_load_cache()
    return cached if cached is not None else set()


# ── External lookups ─────────────────────────────────────────────────────────


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
            on_readings=[
                to_katakana(r) for r in kanji_data.get("on_readings", [])
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
) -> LookupResult:
    """Fetch and parse all data for a query. Raises on Jisho failure."""
    results = search_jisho(query)

    if not results:
        return LookupResult(query=query, vocabulary=[], kanji=[])

    in_anki = query in anki_words
    exact = [r for r in results if is_exact_match(r, query)]
    to_show = exact if exact else results[:5]

    wk_vocab: dict | None = None
    wk_readings_set: set[str] = set()
    if exact:
        jisho_reading = (
            exact[0].get("japanese", [{}])[0].get("reading", "")
        )
        wk_candidate = wk_subjects["vocabulary"].get(query)
        if wk_candidate:
            candidate_readings = set(wk_candidate["readings"])
            if jisho_reading in candidate_readings:
                wk_vocab = wk_candidate
                wk_readings_set = candidate_readings

    vocabulary: list[VocabEntry] = []
    for raw in to_show:
        first = raw.get("japanese", [{}])[0]
        reading = first.get("reading", "")
        word = first.get("word", "")
        is_match = word == query or reading == query
        use_wk = (
            wk_vocab is not None
            and is_match
            and reading in wk_readings_set
        )
        vocabulary.append(parse_vocab_entry(
            raw,
            wk_vocab if use_wk else None,
            in_anki=in_anki and is_match,
        ))

    kanji_chars = extract_kanji(query)
    wk_kanji_cache = {
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
        char_in_anki = any(char in word for word in anki_words)
        kanji.append(parse_kanji_entry(
            char, wk_kanji_cache.get(char), kanji_data,
            in_anki=char_in_anki,
        ))

    return LookupResult(query=query, vocabulary=vocabulary, kanji=kanji)


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

        kanji = (
            result.kanji if self.verbose
            else [k for k in result.kanji if k.unknown]
        )
        if kanji:
            title = "Kanji" if self.verbose else "Unknown Kanji"
            self.console.print(Rule(title, style="dim"))
            self.console.print()
            for entry in kanji:
                self._render_kanji(entry)
                self.console.print()

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
            wk_badge = f"{b.wk_prefix}{entry.wk_level}"
            if entry.wk_burned:
                wk_badge += b.burned
            badges.append(wk_badge, style=c.badge_wk)
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
            wk_badge = f"{b.wk_prefix}{entry.wk_level}"
            if entry.wk_burned:
                wk_badge += b.burned
            badges.append(wk_badge, style=c.badge_wk)
        else:
            badges.append(b.not_in_wk, style=c.badge_warning)
        if not entry.is_jouyou:
            badges.append("  ")
            badges.append(b.not_jouyou, style=c.badge_danger)

        body = Text()
        if entry.meanings:
            body.append("  Meanings: ", style=c.text_label)
            body.append(
                ", ".join(entry.meanings) + "\n", style=c.text_value
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
        if not entry.meanings:
            body.append("  No data found\n", style="dim")

        self.console.print(Panel(
            Text.assemble(badges, "\n\n", body),
            title=title,
            title_align="left",
            border_style=(
                c.border_wk if entry.wk_level is not None
                else c.border_default
            ),
            padding=(0, 1),
        ))


class JsonFormatter:
    def output(self, result: LookupResult) -> None:
        data = asdict(result)
        print(json.dumps(data, ensure_ascii=False, indent=2))


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Japanese dictionary lookup"
    )
    parser.add_argument("query", nargs="+", help="Word to look up")
    parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show all kanji, not just unknown ones",
    )
    args = parser.parse_args()

    query = " ".join(args.query)
    config = load_config()
    token = get_wanikani_token()
    wk_subjects = get_wk_subjects(token)
    anki_words = get_anki_words(config.anki_fields)

    try:
        result = lookup(query, wk_subjects, anki_words)
    except requests.RequestException as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            Console(force_terminal=True).print(
                f"[red]Request failed:[/red] {e}"
            )
        sys.exit(1)

    if not result.vocabulary and not result.kanji:
        if args.json:
            print(json.dumps(asdict(result), ensure_ascii=False))
        else:
            Console(force_terminal=True).print(
                f"[yellow]No results for '{query}'[/yellow]"
            )
        sys.exit(0)

    formatter: Formatter
    if args.json:
        formatter = JsonFormatter()
    else:
        formatter = RichFormatter(
            Console(force_terminal=True),
            config.colors,
            config.badges,
            verbose=args.verbose,
        )

    formatter.output(result)


main()
