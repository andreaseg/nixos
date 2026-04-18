from jisho.model import KanjiEntry


def _make_kanji(**kwargs):
    defaults = dict(
        character="猫", meanings=[], on_readings=[], kun_readings=[],
        is_jouyou=False, wk_level=None, wk_burned=False, in_anki=False,
        jlpt=None,
    )
    return KanjiEntry(**{**defaults, **kwargs})


def test_kanji_unknown_when_not_in_anki_and_not_burned():
    assert _make_kanji().unknown is True


def test_kanji_not_unknown_when_in_anki():
    assert _make_kanji(in_anki=True).unknown is False


def test_kanji_not_unknown_when_burned():
    assert _make_kanji(wk_burned=True).unknown is False
