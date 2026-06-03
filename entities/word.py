from entities.related_word import WordRelation
from entities.example import Example
from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class Word:
    id: Optional[int] = None
    description: Optional[str] = None
    part_of_speech: Optional[int] = None
    stemmed: Optional[str] = None
    raw_form: Optional[str] = None
    examples: list["Example"] = field(default_factory=list)
    related_words: list["WordRelation"] = field(default_factory=list)

    def add_example(self, example: "Example") -> None:
        self.examples.append(example)

    def add_related_word(self, related_word: "WordRelation") -> None:
        self.related_words.append(related_word)
