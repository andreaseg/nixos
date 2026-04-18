import json
from pathlib import Path
from unittest.mock import patch

from jisho.config import (
    Colors, Badges, Cache, Config,
    _parse_colors, _parse_badges, _parse_cache,
    is_nix_managed, default_config_dict,
)


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
    raw = json.loads(json.dumps(default_config_dict()))
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
