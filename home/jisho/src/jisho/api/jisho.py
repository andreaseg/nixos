import requests

from ..model import VocabEntry, KanjiEntry, LookupResult
from ..utils import to_katakana, extract_kanji
from .kanji import lookup_kanji_chars

JISHO_API = "https://jisho.org/api/v1/search/words"


def search_jisho(query: str) -> list[dict]:
    resp = requests.get(JISHO_API, params={"keyword": query}, timeout=10)
    resp.raise_for_status()
    return resp.json().get("data", [])


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
    # jouyou grade and JLPT come from kanjiapi regardless of which source
    # we use for meanings/readings, so compute them up front.
    is_jouyou = (
        kanji_data is not None and kanji_data.get("grade") is not None
    )
    jlpt = kanji_data.get("jlpt") if kanji_data else None

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
            jlpt=jlpt,
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
            jlpt=jlpt,
        )

    return KanjiEntry(
        character=kanji,
        meanings=[],
        on_readings=[],
        kun_readings=[],
        is_jouyou=False,
        in_anki=in_anki,
    )


def lookup(
    query: str,
    wk_subjects: dict,
    anki_words: set[str],
    limit: int | None = 5,
) -> LookupResult:
    """Fetch and parse all data for a query. Raises on Jisho failure."""
    results = search_jisho(query)

    if not results:
        return LookupResult(query=query, vocabulary=[], kanji=[])

    exact = [r for r in results if is_exact_match(r, query)]

    # When the query has an exact match, show only those entries.
    pool = exact if exact else results
    to_show = pool if limit is None else pool[:limit]
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

        vocabulary.append(parse_vocab_entry(raw, wk, in_anki=entry_in_anki))

    # Fall back to the first result's word when the query has no kanji
    # (e.g. searching by reading ねこ or meaning cat).
    first_word = (
        pool[0].get("japanese", [{}])[0].get("word", "") if pool else ""
    )
    kanji_chars = extract_kanji(query) or extract_kanji(first_word)
    wk_kanji = {
        k: wk_subjects["kanji"][k]
        for k in kanji_chars
        if k in wk_subjects["kanji"]
    }

    kanji_api = lookup_kanji_chars(kanji_chars)
    kanji: list[KanjiEntry] = []
    for char in kanji_chars:
        # Mark a kanji as known if it appears in any Anki word, not just
        # as a standalone card — knowing 猫缶 implies exposure to 猫.
        char_in_anki = any(char in w for w in anki_words)
        kanji.append(parse_kanji_entry(
            char, wk_kanji.get(char), kanji_api.get(char),
            in_anki=char_in_anki,
        ))

    return LookupResult(
        query=query,
        vocabulary=vocabulary,
        kanji=kanji,
        more_vocabulary=more,
    )
