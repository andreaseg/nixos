from jisho.utils import to_katakana, extract_kanji, elide_shared_katakana


def test_to_katakana_hiragana():
    assert to_katakana("ねこ") == "ネコ"
    assert to_katakana("いぬ") == "イヌ"


def test_to_katakana_non_hiragana_unchanged():
    assert to_katakana("ネコ") == "ネコ"   # already katakana
    assert to_katakana("猫") == "猫"        # kanji unchanged
    assert to_katakana("abc") == "abc"       # latin unchanged


def test_extract_kanji_basic():
    assert extract_kanji("猫と犬") == ["猫", "犬"]


def test_extract_kanji_deduplicates():
    assert extract_kanji("猫猫犬") == ["猫", "犬"]


def test_extract_kanji_no_kanji():
    assert extract_kanji("ねこ") == []
    assert extract_kanji("cat") == []


def test_elide_shared_katakana_leading():
    assert elide_shared_katakana("トラ猫", "トラねこ") == "…ねこ"


def test_elide_shared_katakana_trailing():
    assert elide_shared_katakana("猫キャット", "ねこキャット") == "ねこ…"


def test_elide_shared_katakana_both():
    assert elide_shared_katakana(
        "トラ猫キャット", "トラねこキャット"
    ) == "…ねこ…"


def test_elide_shared_katakana_no_match():
    assert elide_shared_katakana("黒猫", "くろねこ") == "くろねこ"


def test_elide_shared_katakana_full_match_unchanged():
    # If elision would consume the entire reading, return it as-is
    assert elide_shared_katakana("キャット", "キャット") == "キャット"


def test_elide_shared_katakana_empty():
    assert elide_shared_katakana("猫", "") == ""
