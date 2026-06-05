from dataclasses import dataclass
from typing import Optional
from entities.relation_type import RelationType

@dataclass(slots=True)
class WordRelation:
    word_id_1: Optional[int] = None
    word_id_2: Optional[int] = None
    relation_type: Optional[RelationType] = None