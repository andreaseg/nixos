import json
import sys
from pathlib import Path

from .config import Colors, Badges, Cache, JISHO_CONFIG_FILE


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
