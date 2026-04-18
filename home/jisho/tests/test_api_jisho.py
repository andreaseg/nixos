from jisho.api.jisho import parse_vocab_entry, parse_kanji_entry


_RAW_VOCAB = {
    "japanese": [{"word": "猫", "reading": "ねこ"}],
    "is_common": True,
    "jlpt": ["jlpt-n5"],
    "senses": [
        {"english_definitions": ["cat", "pussy cat"]},
        {"english_definitions": ["pussycat"]},
    ],
}

_WK_VOCAB = {
    "level": 11,
    "meanings": ["Cat"],
    "readings": ["ねこ"],
    "burned": False,
}

_WK_KANJI = {
    "level": 52,
    "meanings": ["Cat"],
    "on_readings": ["ビョウ"],
    "kun_readings": ["ねこ"],
    "burned": False,
}

_KANJIAPI_DATA = {
    "grade": 8,
    "jlpt": 2,
    "meanings": ["cat"],
    "on_readings": ["BYO"],
    "kun_readings": ["neko"],
}


def test_parse_vocab_entry_jisho_path():
    e = parse_vocab_entry(_RAW_VOCAB, None)
    assert e.word == "猫"
    assert e.reading == "ねこ"
    assert e.meanings == ["cat", "pussy cat", "pussycat"]
    assert e.is_common is True
    assert e.wk_level is None
    assert e.wk_burned is False
    assert e.in_anki is False


def test_parse_vocab_entry_wanikani_path():
    e = parse_vocab_entry(_RAW_VOCAB, _WK_VOCAB)
    assert e.meanings == ["Cat"]
    assert e.reading == "ねこ"
    assert e.wk_level == 11
    assert e.wk_burned is False


def test_parse_vocab_entry_wanikani_burned():
    wk = {**_WK_VOCAB, "burned": True}
    e = parse_vocab_entry(_RAW_VOCAB, wk)
    assert e.wk_burned is True


def test_parse_vocab_entry_wanikani_uses_wk_reading():
    wk = {**_WK_VOCAB, "readings": ["こねこ"]}
    e = parse_vocab_entry(_RAW_VOCAB, wk)
    assert e.reading == "こねこ"


def test_parse_vocab_entry_in_anki():
    e = parse_vocab_entry(_RAW_VOCAB, None, in_anki=True)
    assert e.in_anki is True


def test_parse_kanji_entry_wanikani_path():
    e = parse_kanji_entry("猫", _WK_KANJI, None)
    assert e.character == "猫"
    assert e.meanings == ["Cat"]
    assert e.on_readings == ["ビョウ"]
    assert e.wk_level == 52
    assert e.wk_burned is False


def test_parse_kanji_entry_kanjiapi_path():
    e = parse_kanji_entry("猫", None, _KANJIAPI_DATA)
    assert e.meanings == ["cat"]
    assert e.is_jouyou is True    # grade is not None
    assert e.wk_level is None
    assert e.jlpt == 2


def test_parse_kanji_entry_jlpt_from_kanjiapi_in_wk_path():
    # JLPT comes from kanjiapi even when WK provides meanings/readings
    e = parse_kanji_entry("猫", _WK_KANJI, _KANJIAPI_DATA)
    assert e.jlpt == 2


def test_parse_kanji_entry_no_jlpt():
    e = parse_kanji_entry("猫", None, {"grade": 1, "meanings": []})
    assert e.jlpt is None


def test_parse_kanji_entry_no_data():
    e = parse_kanji_entry("猫", None, None)
    assert e.meanings == []
    assert e.on_readings == []
    assert e.is_jouyou is False


def test_parse_kanji_entry_jouyou_requires_grade():
    e = parse_kanji_entry("猫", None, {"grade": None, "meanings": []})
    assert e.is_jouyou is False
