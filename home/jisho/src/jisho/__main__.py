import argparse
import json
import sys
from dataclasses import asdict

import requests
from rich.console import Console

from .config import load_config
from .api.wanikani import get_wk_subjects
from .api.anki import get_anki_words
from .api.jisho import lookup
from .formatters import Formatter, RichFormatter, CompactFormatter, JsonFormatter
from .config import cmd_init_config


def _limit_type(value: str) -> int | None:
    if value.lower() == "none":
        return None
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid limit {value!r}: use a positive integer or 'none'"
        )
    if n < 1:
        raise argparse.ArgumentTypeError(
            f"limit must be at least 1, got {n}"
        )
    return n


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "init-config":
        force = "--force" in sys.argv[2:]
        cmd_init_config(force)
        return

    config = load_config()
    parser = argparse.ArgumentParser(
        prog="jisho",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Japanese dictionary lookup powered by jisho.org\n"
            "\n"
            "Looks up Japanese words and kanji with optional enrichment\n"
            "from WaniKani and Anki. Results show readings, meanings,\n"
            "JLPT level, and your learning status across both tools."
        ),
        epilog=(
            "wanikani integration:\n"
            "  Set WANIKANI_API_TOKEN or write your token to\n"
            "  ~/.config/wanikani/token. Subject data is cached locally\n"
            "  (see --help for cache TTL config).\n"
            "\n"
            "anki integration:\n"
            "  Requires the AnkiConnect add-on (id: 2055492159) inside\n"
            "  Anki. Configure note type → field mappings in your config\n"
            "  file. Words are cached locally, so Anki only needs to run\n"
            "  occasionally to keep the cache fresh.\n"
            "\n"
            "subcommands:\n"
            "  init-config [--force]\n"
            "      Write a default config to ~/.config/jisho/config.json\n"
            "      for easy editing. Aborts if the file is managed by\n"
            "      Nix home-manager. Use --force to overwrite an\n"
            "      existing unmanaged config.\n"
            "\n"
            "examples:\n"
            "  jisho 猫\n"
            "  jisho 日本語 --format compact\n"
            "  jisho 日本語 -f c\n"
            "  jisho 勉強 --verbose --limit 10\n"
            "  jisho 勉強 -v -l 10\n"
            "  jisho init-config"
        ),
    )
    parser.add_argument("query", nargs="+", help="Word to look up")
    parser.add_argument(
        "-f", "--format", default=config.format,
        choices=["rich", "r", "compact", "c", "json", "j"],
        help="Output format: rich/r, compact/c, json/j (default: rich)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show all kanji, not just unknown ones",
    )
    parser.add_argument(
        "-l", "--limit", type=_limit_type, default=5, metavar="N",
        help="Max vocabulary results (default: 5, 'none' for all)",
    )
    args = parser.parse_args()
    args.format = {"r": "rich", "c": "compact", "j": "json"}.get(args.format, args.format)

    query = " ".join(args.query)
    warnings: list[str] = []

    if config.wanikani_enabled:
        wk_subjects, wk_warnings = get_wk_subjects(config.cache.wk_ttl)
        warnings.extend(wk_warnings)
    else:
        wk_subjects = {"vocabulary": {}, "kanji": {}}

    anki_words, anki_warnings = get_anki_words(
        config.anki_fields, config.cache.anki_stale
    )
    warnings.extend(anki_warnings)

    if warnings:
        warn = Console(stderr=True, force_terminal=True)
        for w in warnings:
            warn.print(f"[yellow]Warning:[/yellow] {w}")

    try:
        result = lookup(query, wk_subjects, anki_words, limit=args.limit)
    except requests.RequestException as e:
        if args.format == "json":
            print(json.dumps({"error": str(e)}))
        else:
            Console(force_terminal=True).print(
                f"[red]Request failed:[/red] {e}"
            )
        sys.exit(1)

    if not result.vocabulary and not result.kanji:
        if args.format == "json":
            print(json.dumps(asdict(result), ensure_ascii=False))
        else:
            Console(force_terminal=True).print(
                f"[yellow]No results for '{query}'[/yellow]"
            )
        sys.exit(0)

    formatter: Formatter
    if args.format == "json":
        formatter = JsonFormatter()
    elif args.format == "compact":
        formatter = CompactFormatter(
            Console(force_terminal=True),
            config.colors,
            config.badges,
            verbose=args.verbose,
        )
    else:
        formatter = RichFormatter(
            Console(force_terminal=True),
            config.colors,
            config.badges,
            verbose=args.verbose,
        )

    formatter.output(result)


if __name__ == "__main__":
    main()
