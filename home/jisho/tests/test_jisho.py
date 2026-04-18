"""Unit tests for the jisho package."""
import json as _json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console as _Console

from jisho.utils import to_katakana, extract_kanji, elide_shared_katakana
from jisho.config import (
    Colors, Badges, Cache, Config,
    _parse_colors, _parse_badges, _parse_cache,
    is_nix_managed, default_config_dict,
)
from jisho.model import VocabEntry, KanjiEntry, LookupResult
from jisho.api.jisho import parse_vocab_entry, parse_kanji_entry
from jisho.api.anki import get_anki_words
from jisho.api.kanji import lookup_kanji_chars
from jisho.formatters import RichFormatter, CompactFormatter
import jisho.api.anki as _anki
import jisho.api.kanji as _kanji


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def test_to_katakana_hiragana():
    assert to_katakana("ねこ") == "ネコ"
    assert to_katakana("いぬ") == "イヌ"


def test_to_katakana_non_hiragana_unchanged():
    assert to_katakana("ネコ") == "ネコ"   # already katakana
    assert to_katakana("猫") == "猫"        # kanji unchanged
    assert to_katakana("abc") == "abc"       # latin unchanged


def test_extract_kanji_basic():
    assert extract_kanji("猫と犬") == ["猫", "犬"]


def test_extract_kanji_deduplicates():
    assert extract_kanji("猫猫犬") == ["猫", "犬"]


def test_extract_kanji_no_kanji():
    assert extract_kanji("ねこ") == []
    assert extract_kanji("cat") == []


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def test_parse_colors_defaults():
    c = _parse_colors({})
    assert c.title == "default"
    assert c.badge_anki == "bold green"
    assert c.badge_wk == "bold magenta"
    assert c.border_default == "blue"
    assert c.text_label == "italic dim"
    assert c.text_reading == "cyan"


def test_parse_colors_overrides():
    c = _parse_colors({
        "title": "red",
        "badge": {"anki": "yellow", "wanikani": "white"},
        "border": {"default": "cyan"},
        "text": {"label": "bold"},
    })
    assert c.title == "red"
    assert c.badge_anki == "yellow"
    assert c.badge_wk == "white"
    assert c.border_default == "cyan"
    assert c.text_label == "bold"
    assert c.badge_common == "green"     # unchanged default


def test_parse_badges_defaults():
    b = _parse_badges({})
    assert b.anki == "★ Anki"
    assert b.wk_prefix == "⬡ WaniKani L"
    assert b.burned == " 🔥"
    assert b.not_in_wk == "⚠ not in WaniKani"
    assert b.not_jouyou == "⚠ not jouyou"


def test_parse_badges_camel_case_keys():
    # Verifies the camelCase→snake_case JSON key mapping
    b = _parse_badges({
        "wkPrefix": "◆ WK L",
        "jlptPrefix": "JLPT-",
        "notInWk": "✗ no WK",
        "notJouyou": "✗ rare",
    })
    assert b.wk_prefix == "◆ WK L"
    assert b.jlpt_prefix == "JLPT-"
    assert b.not_in_wk == "✗ no WK"
    assert b.not_jouyou == "✗ rare"
    assert b.anki == "★ Anki"           # unchanged default


def test_parse_cache_defaults():
    c = _parse_cache({})
    assert c.wk_ttl == 604800
    assert c.anki_stale == 604800


def test_parse_cache_overrides():
    c = _parse_cache({"wkTtl": 3600, "ankiStaleTtl": 7200})
    assert c.wk_ttl == 3600
    assert c.anki_stale == 7200


# ---------------------------------------------------------------------------
# Parsing: VocabEntry
# ---------------------------------------------------------------------------

_RAW_VOCAB = {
    "japanese": [{"word": "猫", "reading": "ねこ"}],
    "is_common": True,
    "jlpt": ["jlpt-n5"],
    "senses": [
        {"english_definitions": ["cat", "pussy cat"]},
        {"english_definitions": ["pussycat"]},
    ],
}

_WK_VOCAB = {
    "level": 11,
    "meanings": ["Cat"],
    "readings": ["ねこ"],
    "burned": False,
}


def test_parse_vocab_entry_jisho_path():
    e = parse_vocab_entry(_RAW_VOCAB, None)
    assert e.word == "猫"
    assert e.reading == "ねこ"
    assert e.meanings == ["cat", "pussy cat", "pussycat"]
    assert e.is_common is True
    assert e.wk_level is None
    assert e.wk_burned is False
    assert e.in_anki is False


def test_parse_vocab_entry_wanikani_path():
    e = parse_vocab_entry(_RAW_VOCAB, _WK_VOCAB)
    assert e.meanings == ["Cat"]
    assert e.reading == "ねこ"
    assert e.wk_level == 11
    assert e.wk_burned is False


def test_parse_vocab_entry_wanikani_burned():
    wk = {**_WK_VOCAB, "burned": True}
    e = parse_vocab_entry(_RAW_VOCAB, wk)
    assert e.wk_burned is True


def test_parse_vocab_entry_wanikani_uses_wk_reading():
    wk = {**_WK_VOCAB, "readings": ["こねこ"]}
    e = parse_vocab_entry(_RAW_VOCAB, wk)
    assert e.reading == "こねこ"


def test_parse_vocab_entry_in_anki():
    e = parse_vocab_entry(_RAW_VOCAB, None, in_anki=True)
    assert e.in_anki is True


# ---------------------------------------------------------------------------
# Parsing: KanjiEntry
# ---------------------------------------------------------------------------

_WK_KANJI = {
    "level": 52,
    "meanings": ["Cat"],
    "on_readings": ["ビョウ"],
    "kun_readings": ["ねこ"],
    "burned": False,
}

_KANJIAPI_DATA = {
    "grade": 8,
    "jlpt": 2,
    "meanings": ["cat"],
    "on_readings": ["BYO"],
    "kun_readings": ["neko"],
}


def test_parse_kanji_entry_wanikani_path():
    e = parse_kanji_entry("猫", _WK_KANJI, None)
    assert e.character == "猫"
    assert e.meanings == ["Cat"]
    assert e.on_readings == ["ビョウ"]
    assert e.wk_level == 52
    assert e.wk_burned is False


def test_parse_kanji_entry_kanjiapi_path():
    e = parse_kanji_entry("猫", None, _KANJIAPI_DATA)
    assert e.meanings == ["cat"]
    assert e.is_jouyou is True    # grade is not None
    assert e.wk_level is None
    assert e.jlpt == 2


def test_parse_kanji_entry_jlpt_from_kanjiapi_in_wk_path():
    # JLPT comes from kanjiapi even when WK provides meanings/readings
    e = parse_kanji_entry("猫", _WK_KANJI, _KANJIAPI_DATA)
    assert e.jlpt == 2


def test_parse_kanji_entry_no_jlpt():
    e = parse_kanji_entry("猫", None, {"grade": 1, "meanings": []})
    assert e.jlpt is None


def test_parse_kanji_entry_no_data():
    e = parse_kanji_entry("猫", None, None)
    assert e.meanings == []
    assert e.on_readings == []
    assert e.is_jouyou is False


def test_parse_kanji_entry_jouyou_requires_grade():
    e = parse_kanji_entry("猫", None, {"grade": None, "meanings": []})
    assert e.is_jouyou is False


# ---------------------------------------------------------------------------
# KanjiEntry.unknown property
# ---------------------------------------------------------------------------

def _make_kanji(**kwargs):
    defaults = dict(
        character="猫", meanings=[], on_readings=[], kun_readings=[],
        is_jouyou=False, wk_level=None, wk_burned=False, in_anki=False,
        jlpt=None,
    )
    return KanjiEntry(**{**defaults, **kwargs})


def test_kanji_unknown_when_not_in_anki_and_not_burned():
    assert _make_kanji().unknown is True


def test_kanji_not_unknown_when_in_anki():
    assert _make_kanji(in_anki=True).unknown is False


def test_kanji_not_unknown_when_burned():
    assert _make_kanji(wk_burned=True).unknown is False


# ---------------------------------------------------------------------------
# Anki word fetching and warnings
# ---------------------------------------------------------------------------

_FIELDS = {"My Note Type": "Word Field"}


def test_get_anki_words_live_success():
    live = {"猫", "犬"}
    with patch.object(_anki, "_fetch_words", return_value=live):
        with patch.object(_anki, "_save_cache"):
            words, warnings = get_anki_words(_FIELDS, stale=604800)
    assert words == live
    assert warnings == []


def test_get_anki_words_no_fields_no_warning():
    with patch.object(_anki, "_fetch_words", return_value=None):
        words, warnings = get_anki_words({}, stale=604800)
    assert words == set()
    assert warnings == []


def test_get_anki_words_no_cache_warns():
    with patch.object(_anki, "_fetch_words", return_value=None):
        with patch.object(_anki, "_load_cache", return_value=None):
            words, warnings = get_anki_words(_FIELDS, stale=604800)
    assert words == set()
    assert len(warnings) == 1
    assert "no cache" in warnings[0].lower()


def test_get_anki_words_stale_cache_warns():
    cached = ({"猫"}, True)  # (words, is_stale=True)
    with patch.object(_anki, "_fetch_words", return_value=None):
        with patch.object(_anki, "_load_cache", return_value=cached):
            words, warnings = get_anki_words(_FIELDS, stale=604800)
    assert "猫" in words
    assert len(warnings) == 1
    assert "stale" in warnings[0].lower()


def test_get_anki_words_fresh_cache_no_warning():
    cached = ({"猫"}, False)  # (words, is_stale=False)
    with patch.object(_anki, "_fetch_words", return_value=None):
        with patch.object(_anki, "_load_cache", return_value=cached):
            words, warnings = get_anki_words(_FIELDS, stale=604800)
    assert "猫" in words
    assert warnings == []


# ---------------------------------------------------------------------------
# elide_shared_katakana
# ---------------------------------------------------------------------------


def test_elide_shared_katakana_leading():
    assert elide_shared_katakana("トラ猫", "トラねこ") == "…ねこ"


def test_elide_shared_katakana_trailing():
    assert elide_shared_katakana("猫キャット", "ねこキャット") == "ねこ…"


def test_elide_shared_katakana_both():
    assert elide_shared_katakana(
        "トラ猫キャット", "トラねこキャット"
    ) == "…ねこ…"


def test_elide_shared_katakana_no_match():
    assert elide_shared_katakana("黒猫", "くろねこ") == "くろねこ"


def test_elide_shared_katakana_full_match_unchanged():
    # If elision would consume the entire reading, return it as-is
    assert elide_shared_katakana("キャット", "キャット") == "キャット"


def test_elide_shared_katakana_empty():
    assert elide_shared_katakana("猫", "") == ""


# ---------------------------------------------------------------------------
# init-config
# ---------------------------------------------------------------------------


def test_default_config_dict_structure():
    d = default_config_dict()
    assert "colors" in d
    assert "badge" in d["colors"]
    assert "border" in d["colors"]
    assert "text" in d["colors"]
    assert "badges" in d
    assert "anki" in d
    assert "cache" in d
    assert "format" in d


def test_default_config_dict_roundtrips():
    raw = _json.loads(_json.dumps(default_config_dict()))
    # At minimum, the dict must be valid JSON and parse without error.
    anki = raw.get("anki", {})
    parsed = Config(
        colors=_parse_colors(raw.get("colors", {})),
        badges=_parse_badges(raw.get("badges", {})),
        anki_fields=anki.get("fields", {}),
        cache=_parse_cache(raw.get("cache", {})),
        format=raw.get("format", "rich"),
    )
    assert parsed.format == "rich"
    assert parsed.colors.title == Colors().title
    assert parsed.badges.anki == Badges().anki
    assert parsed.cache.wk_ttl == Cache().wk_ttl


def test_is_nix_managed_regular_file(tmp_path):
    f = tmp_path / "config.json"
    f.write_text("{}")
    assert is_nix_managed(f) is False


def test_is_nix_managed_nix_store_symlink(tmp_path):
    target = tmp_path / "config.json"
    target.write_text("{}")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with patch.object(link.__class__, "resolve",
                      return_value=Path("/nix/store/abc/config.json")):
        assert is_nix_managed(link) is True


# ---------------------------------------------------------------------------
# Kanji cache
# ---------------------------------------------------------------------------


def test_lookup_kanji_chars_uses_cache(tmp_path):
    cached = {"猫": {"meanings": ["cat"]}}
    cache_path = tmp_path / "k.json"
    cache_path.write_text(_json.dumps(cached))
    with patch.object(_kanji, "KANJI_CACHE_FILE", cache_path):
        with patch.object(_kanji, "_fetch_one") as mock_fetch:
            result = lookup_kanji_chars(["猫"])
    mock_fetch.assert_not_called()
    assert result["猫"] == {"meanings": ["cat"]}


def test_lookup_kanji_chars_fetches_missing(tmp_path):
    cache_path = tmp_path / "k.json"
    with patch.object(_kanji, "KANJI_CACHE_FILE", cache_path):
        with patch.object(
            _kanji, "_fetch_one",
            return_value={"meanings": ["dog"]},
        ):
            result = lookup_kanji_chars(["犬"])
    assert result["犬"] == {"meanings": ["dog"]}
    assert cache_path.exists()


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _console() -> tuple[_Console, StringIO]:
    buf = StringIO()
    return _Console(file=buf, no_color=True, width=200), buf


_VOCAB_ENTRY = VocabEntry(
    word="猫", reading="ねこ", is_common=True,
    jlpt=["jlpt-n5"], meanings=["cat"],
)
_UNKNOWN_KANJI = KanjiEntry(
    character="猫", meanings=["cat"],
    on_readings=["ビョウ"], kun_readings=["ねこ"],
    is_jouyou=False, jlpt=2,
)
_RESULT_WITH_KANJI = LookupResult(
    query="猫", vocabulary=[_VOCAB_ENTRY], kanji=[_UNKNOWN_KANJI],
)


def test_compact_vocab_word_in_output():
    console, buf = _console()
    fmt = CompactFormatter(console, Colors(), Badges())
    fmt.output(_RESULT_WITH_KANJI)
    out = buf.getvalue()
    assert "猫" in out
    assert "ねこ" in out
    assert "cat" in out


def test_compact_kanji_separator_shown():
    console, buf = _console()
    fmt = CompactFormatter(console, Colors(), Badges())
    fmt.output(_RESULT_WITH_KANJI)
    assert "── Kanji ──" in buf.getvalue()


def test_compact_known_kanji_hidden():
    known = KanjiEntry(
        character="猫", meanings=["cat"],
        on_readings=["ビョウ"], kun_readings=["ねこ"],
        is_jouyou=False, in_anki=True,
    )
    result = LookupResult(
        query="猫", vocabulary=[_VOCAB_ENTRY], kanji=[known],
    )
    console, buf = _console()
    fmt = CompactFormatter(console, Colors(), Badges())
    fmt.output(result)
    assert "── Kanji ──" not in buf.getvalue()


def test_compact_verbose_shows_known_kanji():
    known = KanjiEntry(
        character="猫", meanings=["cat"],
        on_readings=["ビョウ"], kun_readings=["ねこ"],
        is_jouyou=False, in_anki=True,
    )
    result = LookupResult(
        query="猫", vocabulary=[_VOCAB_ENTRY], kanji=[known],
    )
    console, buf = _console()
    fmt = CompactFormatter(
        console, Colors(), Badges(), verbose=True,
    )
    fmt.output(result)
    assert "── Kanji ──" in buf.getvalue()


def test_compact_col_width_caps_outliers():
    console, _ = _console()
    fmt = CompactFormatter(console, Colors(), Badges())
    # 5 short + 1 very long → 80th-percentile (index 4) = short width
    values = ["ab"] * 5 + ["ab" * 20]
    assert fmt._col_width(values) == 2


def test_compact_more_vocabulary_notice():
    result = LookupResult(
        query="test", vocabulary=[_VOCAB_ENTRY],
        kanji=[], more_vocabulary=3,
    )
    console, buf = _console()
    fmt = CompactFormatter(console, Colors(), Badges())
    fmt.output(result)
    assert "3 more" in buf.getvalue()


def test_rich_vocab_in_output():
    console, buf = _console()
    fmt = RichFormatter(console, Colors(), Badges())
    fmt.output(_RESULT_WITH_KANJI)
    out = buf.getvalue()
    assert "猫" in out
    assert "ねこ" in out
    assert "cat" in out


def test_rich_unknown_kanji_section():
    console, buf = _console()
    fmt = RichFormatter(console, Colors(), Badges())
    fmt.output(_RESULT_WITH_KANJI)
    assert "Unknown Kanji" in buf.getvalue()


def test_rich_verbose_kanji_title():
    console, buf = _console()
    fmt = RichFormatter(
        console, Colors(), Badges(), verbose=True,
    )
    fmt.output(_RESULT_WITH_KANJI)
    out = buf.getvalue()
    assert "Kanji" in out
    assert "Unknown Kanji" not in out
