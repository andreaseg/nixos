import json
import sys
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


def is_nix_managed(path: Path) -> bool:
    # home-manager writes config files as symlinks into /nix/store/
    return path.is_symlink() and "/nix/store/" in str(path.resolve())


def default_config_dict() -> dict:
    """Default config as a dict matching the JSON structure."""
    c = Colors()
    b = Badges()
    ca = Cache()
    return {
        "format": "rich",
        "colors": {
            "title": c.title,
            "badge": {
                "anki": c.badge_anki,
                "wanikani": c.badge_wk,
                "common": c.badge_common,
                "jlpt": c.badge_jlpt,
                "warning": c.badge_warning,
                "danger": c.badge_danger,
            },
            "border": {
                "anki": c.border_anki,
                "wanikani": c.border_wk,
                "default": c.border_default,
            },
            "text": {
                "label": c.text_label,
                "value": c.text_value,
                "reading": c.text_reading,
            },
        },
        "badges": {
            "anki": b.anki,
            "wkPrefix": b.wk_prefix,
            "burned": b.burned,
            "common": b.common,
            "jlptPrefix": b.jlpt_prefix,
            "notInWk": b.not_in_wk,
            "notJouyou": b.not_jouyou,
        },
        "anki": {"fields": {}},
        "cache": {
            "wkTtl": ca.wk_ttl,
            "ankiStaleTtl": ca.anki_stale,
        },
        "wanikani": {"enable": False},
    }


def cmd_init_config(force: bool) -> None:
    if is_nix_managed(JISHO_CONFIG_FILE):
        print(
            "error: config is managed by Nix home-manager —"
            " edit programs.jisho in your Nix config instead.",
            file=sys.stderr,
        )
        sys.exit(1)
    if JISHO_CONFIG_FILE.exists() and not force:
        print(
            f"error: config already exists at {JISHO_CONFIG_FILE}"
            " — use --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)
    JISHO_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    JISHO_CONFIG_FILE.write_text(
        json.dumps(default_config_dict(), ensure_ascii=False, indent=2)
    )
    print(f"Config written to {JISHO_CONFIG_FILE}")
