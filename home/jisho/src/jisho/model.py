from dataclasses import dataclass


@dataclass
class VocabEntry:
    word: str
    reading: str
    is_common: bool
    jlpt: list[str]
    meanings: list[str]
    wk_level: int | None = None
    wk_burned: bool = False
    in_anki: bool = False


@dataclass
class KanjiEntry:
    character: str
    meanings: list[str]
    on_readings: list[str]
    kun_readings: list[str]
    is_jouyou: bool
    wk_level: int | None = None
    wk_burned: bool = False
    in_anki: bool = False
    jlpt: int | None = None

    @property
    def unknown(self) -> bool:
        return not self.in_anki and not self.wk_burned


@dataclass
class LookupResult:
    query: str
    vocabulary: list[VocabEntry]
    kanji: list[KanjiEntry]
    more_vocabulary: int = 0
