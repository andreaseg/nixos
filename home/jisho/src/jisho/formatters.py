import json
from dataclasses import asdict
from typing import Protocol

from rich.cells import cell_len
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from .config import Colors, Badges
from .model import VocabEntry, KanjiEntry, LookupResult
from .utils import elide_shared_katakana


class Formatter(Protocol):
    def output(self, result: LookupResult) -> None: ...


class RichFormatter:
    def __init__(
        self,
        console: Console,
        colors: Colors,
        badges: Badges,
        verbose: bool = False,
        kanji_only: bool = False,
    ) -> None:
        self.console = console
        self.colors = colors
        self.badges = badges
        self.verbose = verbose
        self.kanji_only = kanji_only

    def output(self, result: LookupResult) -> None:
        if not self.kanji_only:
            for entry in result.vocabulary:
                self._render_vocab(entry)
                self.console.print()

            if result.more_vocabulary:
                self.console.print(
                    f"  [dim]… {result.more_vocabulary} more result"
                    f"{'s' if result.more_vocabulary > 1 else ''}"
                    " — use --limit to show more[/dim]"
                )
                self.console.print()

        kanji = (
            result.kanji if self.verbose
            else [k for k in result.kanji if k.unknown]
        )
        if kanji:
            title = "Kanji" if self.verbose else "Unknown Kanji"
            self.console.print(
                Rule(f"[dim]{title}[/dim]", style="dim")
            )
            self.console.print()
            for entry in kanji:
                self._render_kanji(entry)
                self.console.print()

    def _wk_badge_text(self, level: int, burned: bool) -> str:
        text = f"{self.badges.wk_prefix}{level}"
        if burned:
            text += self.badges.burned
        return text

    def _render_vocab(self, entry: VocabEntry) -> None:
        c = self.colors
        b = self.badges
        title = Text()
        title.append(entry.word or entry.reading, style=c.title)

        badges = Text()
        if entry.in_anki:
            badges.append(b.anki, style=c.badge_anki)
            badges.append("  ")
        if entry.wk_level is not None:
            badges.append(
                self._wk_badge_text(entry.wk_level, entry.wk_burned),
                style=c.badge_wk,
            )
            badges.append("  ")
        if entry.is_common:
            badges.append(b.common, style=c.badge_common)
        if entry.jlpt:
            if entry.is_common:
                badges.append("  ")
            jlpt_str = entry.jlpt[0].replace("jlpt-", "").upper()
            badges.append(f"{b.jlpt_prefix}{jlpt_str}", style=c.badge_jlpt)

        body = Text()
        body.append("  Readings: ", style=c.text_label)
        body.append(entry.reading + "\n", style=c.text_value)
        body.append("  Meanings: ", style=c.text_label)
        body.append(", ".join(entry.meanings) + "\n", style=c.text_value)

        # Border colour reflects data source priority: Anki > WK > default
        border = c.border_anki if entry.in_anki else (
            c.border_wk if entry.wk_level is not None
            else c.border_default
        )
        content = Text.assemble(badges, "\n\n", body) if badges else body
        self.console.print(Panel(
            content,
            title=title,
            title_align="left",
            border_style=border,
            padding=(0, 1),
        ))

    def _render_kanji(self, entry: KanjiEntry) -> None:
        c = self.colors
        b = self.badges
        title = Text(entry.character, style=c.title)

        badges = Text()
        if entry.in_anki:
            badges.append(b.anki, style=c.badge_anki)
            badges.append("  ")
        if entry.wk_level is not None:
            badges.append(
                self._wk_badge_text(entry.wk_level, entry.wk_burned),
                style=c.badge_wk,
            )
        else:
            badges.append(b.not_in_wk, style=c.badge_warning)
        if not entry.is_jouyou:
            badges.append("  ")
            badges.append(b.not_jouyou, style=c.badge_danger)
        if entry.jlpt is not None:
            badges.append(
                f"  {b.jlpt_prefix}N{entry.jlpt}", style=c.badge_jlpt
            )

        body = Text()
        if entry.meanings or entry.on_readings or entry.kun_readings:
            if entry.meanings:
                body.append("  Meanings: ", style=c.text_label)
                body.append(
                    ", ".join(entry.meanings) + "\n", style=c.text_value
                )
            if entry.on_readings:
                body.append("  On: ", style=c.text_label)
                body.append(
                    ", ".join(entry.on_readings) + "\n", style=c.text_value
                )
            if entry.kun_readings:
                body.append("  Kun: ", style=c.text_label)
                body.append(
                    ", ".join(entry.kun_readings) + "\n", style=c.text_value
                )
        else:
            body.append("  No data found\n", style="dim")

        content = Text.assemble(badges, "\n\n", body) if badges else body
        self.console.print(Panel(
            content,
            title=title,
            title_align="left",
            border_style=(
                c.border_wk if entry.wk_level is not None
                else c.border_default
            ),
            padding=(0, 1),
        ))


class CompactFormatter:
    """One line per entry: {word} {reading} {meanings} {badges}."""

    def __init__(
        self,
        console: Console,
        colors: Colors,
        badges: Badges,
        verbose: bool = False,
        kanji_only: bool = False,
    ) -> None:
        self.console = console
        self.colors = colors
        self.badges = badges
        self.verbose = verbose
        self.kanji_only = kanji_only

    def _col_width(self, values: list[str]) -> int:
        """80th-percentile display width — caps outliers without truncating."""
        if not values:
            return 0
        widths = sorted(cell_len(v) for v in values)
        return widths[int(len(widths) * 0.8)]

    def output(self, result: LookupResult) -> None:
        kanji = (
            result.kanji if self.verbose
            else [k for k in result.kanji if k.unknown]
        )
        # Pre-compute shared column widths across vocab and kanji so all
        # lines align at the same meaning column.
        vocab_for_width = [] if self.kanji_only else result.vocabulary
        word_w = self._col_width(
            [e.word or e.reading for e in vocab_for_width]
            + [e.character for e in kanji]
        )
        read_w = self._col_width(
            [e.reading for e in vocab_for_width if e.word]
            + [", ".join(e.on_readings + e.kun_readings) for e in kanji]
        )
        if not self.kanji_only:
            for entry in result.vocabulary:
                self._render_vocab(entry, word_w, read_w)

            if result.more_vocabulary:
                self.console.print(
                    f"[dim]… {result.more_vocabulary} more result"
                    f"{'s' if result.more_vocabulary > 1 else ''}"
                    " — use --limit to show more[/dim]"
                )

        if kanji:
            if not self.kanji_only:
                self.console.print("[dim]── Kanji ──[/dim]")
            for entry in kanji:
                self._render_kanji(entry, word_w, read_w)

    def _render_vocab(
        self,
        entry: VocabEntry,
        word_w: int = 0,
        read_w: int = 0,
    ) -> None:
        c = self.colors
        line = Text()
        word = entry.word or entry.reading
        w = cell_len(word)
        line.append(word, style=c.title)
        if entry.word:
            # Pad each column separately; outliers get one space
            line.append(" " * max(1, word_w - w + 1))
            reading = elide_shared_katakana(entry.word, entry.reading)
            r = cell_len(reading)
            line.append(reading, style=c.text_reading)
            line.append(" " * max(1, read_w - r + 1))
        else:
            # No reading — pad both columns together so the meaning
            # column stays aligned even when the word overflows word_w
            line.append(" " * max(1, word_w + read_w + 2 - w))
        line.append(", ".join(entry.meanings), style=c.text_value)
        if entry.in_anki:
            line.append("  A", style=c.badge_anki)
        if entry.wk_level is not None:
            wk = f"  🐢{entry.wk_level}"
            if entry.wk_burned:
                wk += "🔥"
            line.append(wk, style=c.badge_wk)
        if entry.is_common:
            line.append("  C", style=c.badge_common)
        if entry.jlpt:
            jlpt_str = entry.jlpt[0].replace("jlpt-", "").upper()
            line.append(f"  {jlpt_str}", style=c.badge_jlpt)
        self.console.print(line, no_wrap=True, overflow="ellipsis")

    def _render_kanji(
        self,
        entry: KanjiEntry,
        word_w: int = 0,
        read_w: int = 0,
    ) -> None:
        c = self.colors
        line = Text()
        w = cell_len(entry.character)
        line.append(entry.character, style=c.title)
        readings = ", ".join(entry.on_readings + entry.kun_readings)
        if readings:
            line.append(" " * max(1, word_w - w + 1))
            r = cell_len(readings)
            line.append(readings, style=c.text_reading)
            line.append(" " * max(1, read_w - r + 1))
        else:
            line.append(" " * max(1, word_w + read_w + 2 - w))
        if entry.meanings:
            line.append(", ".join(entry.meanings), style=c.text_value)
        if entry.in_anki:
            line.append("  A", style=c.badge_anki)
        if entry.wk_level is not None:
            wk = f"  🐢{entry.wk_level}"
            if entry.wk_burned:
                wk += "🔥"
            line.append(wk, style=c.badge_wk)
        else:
            line.append("  ∅🐢", style=c.badge_warning)
        if not entry.is_jouyou:
            line.append("  ∅J", style=c.badge_danger)
        if entry.jlpt is not None:
            line.append(f"  N{entry.jlpt}", style=c.badge_jlpt)
        self.console.print(line, no_wrap=True, overflow="ellipsis")


class JsonFormatter:
    def output(self, result: LookupResult) -> None:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
