import json
from unittest.mock import patch

from jisho.api.kanji import lookup_kanji_chars
import jisho.api.kanji as _kanji


def test_lookup_kanji_chars_uses_cache(tmp_path):
    cached = {"猫": {"meanings": ["cat"]}}
    cache_path = tmp_path / "k.json"
    cache_path.write_text(json.dumps(cached))
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
