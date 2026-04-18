import os
import sys
import requests
from dataclasses import dataclass
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

WANIKANI_TOKEN_FILE = Path.home() / ".config" / "wanikani" / "token"
WANIKANI_API = "https://api.wanikani.com/v2"
KANJIAPI = "https://kanjiapi.dev/v1/kanji"
ANKI_CONNECT = "http://localhost:8765"

# Maps Anki note type names to the field containing the vocabulary word.
# Add additional note types here as needed.
ANKI_VOCAB_FIELDS: dict[str, str] = {
    "Migaku Japanese CUSTOM STYLING": "Target Word Simplified",
}


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
    in_anki: bool = False


@dataclass
class KanjiEntry:
    character: str
    meanings: list[str]
    on_readings: list[str]
    kun_readings: list[str]
    is_jouyou: bool
    wk_level: int | None = None


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


def anki_request(action: str, **params) -> object:
    payload = {"action": action, "version": 6, "params": params}
    resp = requests.post(ANKI_CONNECT, json=payload, timeout=3)
    resp.raise_for_status()
    result = resp.json()
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result["result"]


def search_anki(query: str) -> bool:
    try:
        for note_type, field_name in ANKI_VOCAB_FIELDS.items():
            search = f'note:"{note_type}" "{field_name}:{query}"'
            note_ids = anki_request("findNotes", query=search)
            if note_ids:
                return True
    except (requests.RequestException, RuntimeError, KeyError):
        pass
    return False


def search_jisho(query: str) -> list[dict]:
    resp = requests.get(
        "https://jisho.org/api/v1/search/words",
        params={"keyword": query},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def search_wanikani_vocab(query: str, token: str) -> dict | None:
    resp = requests.get(
        f"{WANIKANI_API}/subjects",
        params={"types": "vocabulary,kanji", "slugs": query},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else None


def search_wanikani_kanji(
    kanji_list: list[str], token: str
) -> dict[str, dict]:
    resp = requests.get(
        f"{WANIKANI_API}/subjects",
        params={"types": "kanji", "slugs": ",".join(kanji_list)},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return {s["data"]["slug"]: s for s in resp.json().get("data", [])}


def lookup_kanji_data(kanji: str) -> dict | None:
    resp = requests.get(f"{KANJIAPI}/{kanji}", timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


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
        wk_data = wk_subject["data"]
        return VocabEntry(
            word=word,
            reading=reading,
            is_common=raw.get("is_common", False),
            jlpt=raw.get("jlpt", []),
            senses=[],
            wk_level=wk_data.get("level"),
            wk_meanings=[
                m["meaning"] for m in wk_data.get("meanings", [])
            ],
            wk_readings=[
                r["reading"] for r in wk_data.get("readings", [])
            ],
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
) -> KanjiEntry:
    is_jouyou = (
        kanji_data is not None and kanji_data.get("grade") is not None
    )

    if wk_subject:
        wk_data = wk_subject["data"]
        return KanjiEntry(
            character=kanji,
            meanings=[m["meaning"] for m in wk_data.get("meanings", [])],
            on_readings=[
                to_katakana(r["reading"])
                for r in wk_data.get("readings", [])
                if r.get("type") == "onyomi"
            ],
            kun_readings=[
                r["reading"]
                for r in wk_data.get("readings", [])
                if r.get("type") == "kunyomi"
            ],
            is_jouyou=is_jouyou,
            wk_level=wk_data.get("level"),
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
        )

    return KanjiEntry(
        character=kanji,
        meanings=[],
        on_readings=[],
        kun_readings=[],
        is_jouyou=False,
    )


def render_vocab_entry(entry: VocabEntry, console: Console) -> None:
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
        badges.append(
            f"⬡ WaniKani L{entry.wk_level}", style="bold magenta"
        )
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
        body.append(", ".join(entry.wk_meanings) + "\n", style="white")
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
                    pos_label = "  " + " · ".join(sense.parts_of_speech)
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
    console.print(Panel(
        content,
        title=title,
        title_align="left",
        border_style=border,
        padding=(0, 1),
    ))


def render_kanji_entry(entry: KanjiEntry, console: Console) -> None:
    title = Text(entry.character, style="bold cyan")

    badges = Text()
    if entry.wk_level is not None:
        badges.append(
            f"⬡ WaniKani L{entry.wk_level}", style="bold magenta"
        )
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
        body.append(", ".join(entry.on_readings) + "\n", style="white")
    if entry.kun_readings:
        body.append("  Kun: ", style="italic dim")
        body.append(", ".join(entry.kun_readings) + "\n", style="white")
    if not entry.meanings:
        body.append("  No data found\n", style="dim")

    console.print(Panel(
        Text.assemble(badges, "\n\n", body),
        title=title,
        title_align="left",
        border_style="magenta" if entry.wk_level is not None else "blue",
        padding=(0, 1),
    ))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: jisho <query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    console = Console(force_terminal=True)
    token = get_wanikani_token()

    try:
        results = search_jisho(query)
    except requests.RequestException as e:
        console.print(f"[red]Request failed:[/red] {e}")
        sys.exit(1)

    if not results:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        sys.exit(0)

    in_anki = search_anki(query)

    exact = [r for r in results if is_exact_match(r, query)]
    to_show = exact if exact else results[:5]

    wk_vocab: dict | None = None
    wk_readings_set: set[str] = set()
    if token and exact:
        try:
            jisho_reading = (
                exact[0].get("japanese", [{}])[0].get("reading", "")
            )
            wk_candidate = search_wanikani_vocab(query, token)
            if wk_candidate:
                candidate_readings = {
                    r["reading"]
                    for r in wk_candidate["data"].get("readings", [])
                }
                if jisho_reading in candidate_readings:
                    wk_vocab = wk_candidate
                    wk_readings_set = candidate_readings
        except requests.RequestException:
            pass

    for raw in to_show:
        first = raw.get("japanese", [{}])[0]
        reading = first.get("reading", "")
        word = first.get("word", "")
        use_wk = (
            wk_vocab is not None
            and (word == query or reading == query)
            and reading in wk_readings_set
        )
        is_match = word == query or reading == query
        entry = parse_vocab_entry(
            raw,
            wk_vocab if use_wk else None,
            in_anki=in_anki and is_match,
        )
        render_vocab_entry(entry, console)
        console.print()

    kanji_chars = extract_kanji(query)
    if not kanji_chars:
        return

    wk_kanji: dict[str, dict] = {}
    if token:
        try:
            wk_kanji = search_wanikani_kanji(kanji_chars, token)
        except requests.RequestException:
            pass

    console.print(Rule("Kanji", style="dim"))
    console.print()

    for kanji in kanji_chars:
        try:
            kanji_data = lookup_kanji_data(kanji)
        except requests.RequestException:
            kanji_data = None
        entry = parse_kanji_entry(
            kanji, wk_kanji.get(kanji), kanji_data
        )
        render_kanji_entry(entry, console)
        console.print()


main()
