from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class WordRelation:
    word_id_1: Optional[int] = None
    word_id_2: Optional[int] = None
    relation_type: Optional[int] = None
