"""Unit tests for jisho.py"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Import jisho as a module (guarded by if __name__ == "__main__")
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "jisho", Path(__file__).parent / "jisho.py"
)
jisho = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jisho)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def test_to_katakana_hiragana():
    assert jisho.to_katakana("ねこ") == "ネコ"
    assert jisho.to_katakana("いぬ") == "イヌ"


def test_to_katakana_non_hiragana_unchanged():
    assert jisho.to_katakana("ネコ") == "ネコ"   # already katakana
    assert jisho.to_katakana("猫") == "猫"        # kanji unchanged
    assert jisho.to_katakana("abc") == "abc"       # latin unchanged


def test_extract_kanji_basic():
    assert jisho.extract_kanji("猫と犬") == ["猫", "犬"]


def test_extract_kanji_deduplicates():
    assert jisho.extract_kanji("猫猫犬") == ["猫", "犬"]


def test_extract_kanji_no_kanji():
    assert jisho.extract_kanji("ねこ") == []
    assert jisho.extract_kanji("cat") == []


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def test_parse_colors_defaults():
    c = jisho._parse_colors({})
    assert c.title == "default"
    assert c.badge_anki == "bold green"
    assert c.badge_wk == "bold magenta"
    assert c.border_default == "blue"
    assert c.text_label == "italic dim"
    assert c.text_reading == "cyan"


def test_parse_colors_overrides():
    c = jisho._parse_colors({
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
    b = jisho._parse_badges({})
    assert b.anki == "★ Anki"
    assert b.wk_prefix == "⬡ WaniKani L"
    assert b.burned == " 🔥"
    assert b.not_in_wk == "⚠ not in WaniKani"
    assert b.not_jouyou == "⚠ not jouyou"


def test_parse_badges_camel_case_keys():
    # Verifies the camelCase→snake_case JSON key mapping
    b = jisho._parse_badges({
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
    c = jisho._parse_cache({})
    assert c.wk_ttl == 604800
    assert c.anki_stale == 604800


def test_parse_cache_overrides():
    c = jisho._parse_cache({"wkTtl": 3600, "ankiStaleTtl": 7200})
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
    e = jisho.parse_vocab_entry(_RAW_VOCAB, None)
    assert e.word == "猫"
    assert e.reading == "ねこ"
    assert e.meanings == ["cat", "pussy cat", "pussycat"]
    assert e.is_common is True
    assert e.wk_level is None
    assert e.wk_burned is False
    assert e.in_anki is False


def test_parse_vocab_entry_wanikani_path():
    e = jisho.parse_vocab_entry(_RAW_VOCAB, _WK_VOCAB)
    assert e.meanings == ["Cat"]
    assert e.reading == "ねこ"
    assert e.wk_level == 11
    assert e.wk_burned is False


def test_parse_vocab_entry_wanikani_burned():
    wk = {**_WK_VOCAB, "burned": True}
    e = jisho.parse_vocab_entry(_RAW_VOCAB, wk)
    assert e.wk_burned is True


def test_parse_vocab_entry_wanikani_uses_wk_reading():
    wk = {**_WK_VOCAB, "readings": ["こねこ"]}
    e = jisho.parse_vocab_entry(_RAW_VOCAB, wk)
    assert e.reading == "こねこ"


def test_parse_vocab_entry_in_anki():
    e = jisho.parse_vocab_entry(_RAW_VOCAB, None, in_anki=True)
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
    e = jisho.parse_kanji_entry("猫", _WK_KANJI, None)
    assert e.character == "猫"
    assert e.meanings == ["Cat"]
    assert e.on_readings == ["ビョウ"]
    assert e.wk_level == 52
    assert e.wk_burned is False


def test_parse_kanji_entry_kanjiapi_path():
    e = jisho.parse_kanji_entry("猫", None, _KANJIAPI_DATA)
    assert e.meanings == ["cat"]
    assert e.is_jouyou is True    # grade is not None
    assert e.wk_level is None
    assert e.jlpt == 2


def test_parse_kanji_entry_jlpt_from_kanjiapi_in_wk_path():
    # JLPT comes from kanjiapi even when WK provides meanings/readings
    e = jisho.parse_kanji_entry("猫", _WK_KANJI, _KANJIAPI_DATA)
    assert e.jlpt == 2


def test_parse_kanji_entry_no_jlpt():
    e = jisho.parse_kanji_entry("猫", None, {"grade": 1, "meanings": []})
    assert e.jlpt is None


def test_parse_kanji_entry_no_data():
    e = jisho.parse_kanji_entry("猫", None, None)
    assert e.meanings == []
    assert e.on_readings == []
    assert e.is_jouyou is False


def test_parse_kanji_entry_jouyou_requires_grade():
    e = jisho.parse_kanji_entry("猫", None, {"grade": None, "meanings": []})
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
    return jisho.KanjiEntry(**{**defaults, **kwargs})


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
    with patch.object(jisho, "anki_fetch_words", return_value=live):
        with patch.object(jisho, "anki_save_cache"):
            words, warnings = jisho.get_anki_words(_FIELDS, stale=604800)
    assert words == live
    assert warnings == []


def test_get_anki_words_no_fields_no_warning():
    with patch.object(jisho, "anki_fetch_words", return_value=None):
        words, warnings = jisho.get_anki_words({}, stale=604800)
    assert words == set()
    assert warnings == []


def test_get_anki_words_no_cache_warns():
    with patch.object(jisho, "anki_fetch_words", return_value=None):
        with patch.object(jisho, "anki_load_cache", return_value=None):
            words, warnings = jisho.get_anki_words(_FIELDS, stale=604800)
    assert words == set()
    assert len(warnings) == 1
    assert "no cache" in warnings[0].lower()


def test_get_anki_words_stale_cache_warns():
    cached = ({"猫"}, True)  # (words, is_stale=True)
    with patch.object(jisho, "anki_fetch_words", return_value=None):
        with patch.object(jisho, "anki_load_cache", return_value=cached):
            words, warnings = jisho.get_anki_words(_FIELDS, stale=604800)
    assert "猫" in words
    assert len(warnings) == 1
    assert "stale" in warnings[0].lower()


def test_get_anki_words_fresh_cache_no_warning():
    cached = ({"猫"}, False)  # (words, is_stale=False)
    with patch.object(jisho, "anki_fetch_words", return_value=None):
        with patch.object(jisho, "anki_load_cache", return_value=cached):
            words, warnings = jisho.get_anki_words(_FIELDS, stale=604800)
    assert "猫" in words
    assert warnings == []


# ---------------------------------------------------------------------------
# elide_shared_katakana
# ---------------------------------------------------------------------------


def test_elide_shared_katakana_leading():
    assert jisho.elide_shared_katakana("トラ猫", "トラねこ") == "…ねこ"


def test_elide_shared_katakana_trailing():
    assert jisho.elide_shared_katakana("猫キャット", "ねこキャット") == "ねこ…"


def test_elide_shared_katakana_both():
    assert jisho.elide_shared_katakana(
        "トラ猫キャット", "トラねこキャット"
    ) == "…ねこ…"


def test_elide_shared_katakana_no_match():
    assert jisho.elide_shared_katakana("黒猫", "くろねこ") == "くろねこ"


def test_elide_shared_katakana_full_match_unchanged():
    # If elision would consume the entire reading, return it as-is
    assert jisho.elide_shared_katakana("キャット", "キャット") == "キャット"


def test_elide_shared_katakana_empty():
    assert jisho.elide_shared_katakana("猫", "") == ""


# ---------------------------------------------------------------------------
# init-config
# ---------------------------------------------------------------------------


def test_default_config_dict_structure():
    d = jisho.default_config_dict()
    assert "colors" in d
    assert "badge" in d["colors"]
    assert "border" in d["colors"]
    assert "text" in d["colors"]
    assert "badges" in d
    assert "anki" in d
    assert "cache" in d
    assert "format" in d


def test_default_config_dict_roundtrips():
    # Writing defaults and reading them back should produce the same config
    # as the no-file fallback.
    import json as _json
    raw = _json.loads(_json.dumps(jisho.default_config_dict()))
    cfg = jisho.load_config.__wrapped__(raw) if hasattr(
        jisho.load_config, "__wrapped__"
    ) else None
    # At minimum, the dict must be valid JSON and parse without error.
    anki = raw.get("anki", {})
    parsed = jisho.Config(
        colors=jisho._parse_colors(raw.get("colors", {})),
        badges=jisho._parse_badges(raw.get("badges", {})),
        anki_fields=anki.get("fields", {}),
        cache=jisho._parse_cache(raw.get("cache", {})),
        format=raw.get("format", "rich"),
    )
    assert parsed.format == "rich"
    assert parsed.colors.title == jisho.Colors().title
    assert parsed.badges.anki == jisho.Badges().anki
    assert parsed.cache.wk_ttl == jisho.Cache().wk_ttl


def test_is_nix_managed_regular_file(tmp_path):
    f = tmp_path / "config.json"
    f.write_text("{}")
    assert jisho.is_nix_managed(f) is False


def test_is_nix_managed_nix_store_symlink(tmp_path):
    target = tmp_path / "config.json"
    target.write_text("{}")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    # Patch resolve to simulate a /nix/store path
    with patch.object(link.__class__, "resolve",
                      return_value=Path("/nix/store/abc/config.json")):
        assert jisho.is_nix_managed(link) is True
