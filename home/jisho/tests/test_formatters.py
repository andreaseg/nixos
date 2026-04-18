from io import StringIO

from rich.console import Console as _Console

from jisho.config import Colors, Badges
from jisho.model import VocabEntry, KanjiEntry, LookupResult
from jisho.formatters import RichFormatter, CompactFormatter


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
    result = LookupResult(query="猫", vocabulary=[_VOCAB_ENTRY], kanji=[known])
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
    result = LookupResult(query="猫", vocabulary=[_VOCAB_ENTRY], kanji=[known])
    console, buf = _console()
    fmt = CompactFormatter(console, Colors(), Badges(), verbose=True)
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
        query="test", vocabulary=[_VOCAB_ENTRY], kanji=[], more_vocabulary=3,
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
    fmt = RichFormatter(console, Colors(), Badges(), verbose=True)
    fmt.output(_RESULT_WITH_KANJI)
    out = buf.getvalue()
    assert "Kanji" in out
    assert "Unknown Kanji" not in out
