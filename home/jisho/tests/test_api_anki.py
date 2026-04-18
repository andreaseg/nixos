from unittest.mock import patch

from jisho.api.anki import get_anki_words
import jisho.api.anki as _anki


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
