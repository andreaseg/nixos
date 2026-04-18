import json
from dataclasses import dataclass
from pathlib import Path

JISHO_CONFIG_FILE = Path.home() / ".config" / "jisho" / "config.json"


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
    wk_ttl: int = 604800
    anki_stale: int = 604800


@dataclass
class Config:
    colors: Colors
    badges: Badges
    anki_fields: dict[str, str]
    cache: Cache
    format: str = "rich"
    wanikani_enabled: bool = False


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
        badge_warning=badge.get("warning", defaults.badge_warning),
        badge_danger=badge.get("danger", defaults.badge_danger),
        border_anki=border.get("anki", defaults.border_anki),
        border_wk=border.get("wanikani", defaults.border_wk),
        border_default=border.get("default", defaults.border_default),
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
        wk = raw.get("wanikani", {})
        return Config(
            colors=_parse_colors(raw.get("colors", {})),
            badges=_parse_badges(raw.get("badges", {})),
            anki_fields=anki.get("fields", {}),
            cache=_parse_cache(raw.get("cache", {})),
            format=raw.get("format", "rich"),
            wanikani_enabled=wk.get("enable", False),
        )
    except (json.JSONDecodeError, KeyError):
        return fallback
