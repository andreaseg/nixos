def _is_katakana(c: str) -> bool:
    return "\u30a0" <= c <= "\u30ff"


def elide_shared_katakana(word: str, reading: str) -> str:
    """Replace katakana shared at word/reading boundaries with …

    When a word and its reading share katakana at the start or end
    (e.g. トラ猫 / トラねこ), those characters are visually obvious
    and can be replaced with … for compact display (→ …ねこ).
    """
    if not word or not reading:
        return reading

    prefix = 0
    for wc, rc in zip(word, reading):
        if _is_katakana(wc) and wc == rc:
            prefix += 1
        else:
            break

    suffix = 0
    for wc, rc in zip(reversed(word), reversed(reading)):
        if _is_katakana(wc) and wc == rc:
            suffix += 1
        else:
            break

    if prefix + suffix >= len(reading):
        return reading

    end = len(reading) - suffix if suffix else len(reading)
    middle = reading[prefix:end]
    return ("…" if prefix else "") + middle + ("…" if suffix else "")


def to_katakana(text: str) -> str:
    # Hiragana (U+3041–U+3096) and katakana (U+30A1–U+30F6) share the
    # same glyph layout with a fixed offset of 0x60.
    return "".join(
        chr(ord(c) + 0x60) if "\u3041" <= c <= "\u3096" else c
        for c in text
    )


def extract_kanji(text: str) -> list[str]:
    # dict.fromkeys preserves first-occurrence order while deduplicating.
    return list(
        dict.fromkeys(c for c in text if "\u4e00" <= c <= "\u9fff")
    )
