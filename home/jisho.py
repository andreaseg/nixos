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

ANKI_CONNECT = "http://localhost:8765"
ANKI_CACHE_FILE = Path.home() / ".cache" / "jisho" / "anki_words.json"
ANKI_CACHE_TTL = 86400  # 1 day in seconds

# Maps Anki note type names to the field containing the vocabulary word.
# Add additional note types here as needed.
ANKI_VOCAB_FIELDS: dict[str, str] = {
    "Migaku Japanese CUSTOM STYLING": "Target Word Simplified",
}


# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class Sense:
    parts_of_speech: list[str]
    definitions: list[str]
    info: list[str]


@dataclass
class VocabEntry:
    word: str
    reading: str
    is_common: bool
    jlpt: list[str]
    senses: list[Sense]
    wk_level: int | None = None
    wk_meanings: list[str] | None = None
    wk_readings: list[str] | None = None
    burned: bool = False
    in_anki: bool = False


@dataclass
class KanjiEntry:
    character: str
    meanings: list[str]
    on_readings: list[str]
    kun_readings: list[str]
    is_jouyou: bool
    wk_level: int | None = None
    burned: bool = False
    in_anki: bool = False

    @property
    def unknown(self) -> bool:
        return not self.in_anki and not self.burned


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


def anki_fetch_words() -> set[str] | None:
    try:
        words: set[str] = set()
        for note_type, field_name in ANKI_VOCAB_FIELDS.items():
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


def get_anki_words() -> set[str]:
    live = anki_fetch_words()
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
        return VocabEntry(
            word=word,
            reading=reading,
            is_common=raw.get("is_common", False),
            jlpt=raw.get("jlpt", []),
            senses=[],
            wk_level=wk_subject["level"],
            wk_meanings=wk_subject["meanings"],
            wk_readings=wk_subject["readings"],
            burned=wk_subject["burned"],
            in_anki=in_anki,
        )

    senses = [
        Sense(
            parts_of_speech=s.get("parts_of_speech", []),
            definitions=s.get("english_definitions", []),
            info=s.get("info", []),
        )
        for s in raw.get("senses", [])
    ]
    return VocabEntry(
        word=word,
        reading=reading,
        is_common=raw.get("is_common", False),
        jlpt=raw.get("jlpt", []),
        senses=senses,
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
            burned=wk_subject["burned"],
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
    def __init__(self, console: Console, verbose: bool = False) -> None:
        self.console = console
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
        title = Text()
        if entry.word:
            title.append(entry.word, style="bold cyan")
            title.append("  ")
            title.append(entry.reading, style="cyan")
        else:
            title.append(entry.reading, style="bold cyan")

        badges = Text()
        if entry.in_anki:
            badges.append("★ Anki", style="bold green")
            badges.append("  ")
        if entry.wk_level is not None:
            wk_badge = f"⬡ WaniKani L{entry.wk_level}"
            if entry.burned:
                wk_badge += " 🔥"
            badges.append(wk_badge, style="bold magenta")
            badges.append("  ")
        if entry.is_common:
            badges.append("● common", style="green")
        if entry.jlpt:
            if entry.is_common:
                badges.append("  ")
            jlpt_str = entry.jlpt[0].replace("jlpt-", "").upper()
            badges.append(f"● {jlpt_str}", style="yellow")

        body = Text()
        if entry.wk_meanings is not None:
            body.append("  Meanings: ", style="italic dim")
            body.append(
                ", ".join(entry.wk_meanings) + "\n", style="white"
            )
            if entry.wk_readings:
                body.append("  Readings: ", style="italic dim")
                body.append(
                    ", ".join(entry.wk_readings) + "\n", style="white"
                )
        else:
            prev_pos: tuple[str, ...] = ()
            for i, sense in enumerate(entry.senses, 1):
                pos_key = tuple(sense.parts_of_speech)
                if pos_key != prev_pos:
                    if i > 1:
                        body.append("\n")
                    if sense.parts_of_speech:
                        pos_label = (
                            "  " + " · ".join(sense.parts_of_speech)
                        )
                        body.append(pos_label + "\n", style="italic dim")
                    prev_pos = pos_key
                body.append(f"  {i}. ", style="bold white")
                body.append(", ".join(sense.definitions), style="white")
                if sense.info:
                    body.append(
                        f"  ({', '.join(sense.info)})", style="dim"
                    )
                body.append("\n")

        border = "green" if entry.in_anki else (
            "magenta" if entry.wk_level is not None else "blue"
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
        title = Text(entry.character, style="bold cyan")

        badges = Text()
        if entry.in_anki:
            badges.append("★ Anki", style="bold green")
            badges.append("  ")
        if entry.wk_level is not None:
            wk_badge = f"⬡ WaniKani L{entry.wk_level}"
            if entry.burned:
                wk_badge += " 🔥"
            badges.append(wk_badge, style="bold magenta")
        else:
            badges.append("⚠ not in WaniKani", style="yellow")
        if not entry.is_jouyou:
            badges.append("  ")
            badges.append("⚠ not jouyou", style="red")

        body = Text()
        if entry.meanings:
            body.append("  Meanings: ", style="italic dim")
            body.append(", ".join(entry.meanings) + "\n", style="white")
        if entry.on_readings:
            body.append("  On: ", style="italic dim")
            body.append(
                ", ".join(entry.on_readings) + "\n", style="white"
            )
        if entry.kun_readings:
            body.append("  Kun: ", style="italic dim")
            body.append(
                ", ".join(entry.kun_readings) + "\n", style="white"
            )
        if not entry.meanings:
            body.append("  No data found\n", style="dim")

        self.console.print(Panel(
            Text.assemble(badges, "\n\n", body),
            title=title,
            title_align="left",
            border_style=(
                "magenta" if entry.wk_level is not None else "blue"
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
    token = get_wanikani_token()
    wk_subjects = get_wk_subjects(token)
    anki_words = get_anki_words()

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
            Console(force_terminal=True), verbose=args.verbose
        )

    formatter.output(result)


main()
