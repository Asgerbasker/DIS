from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Example:
    id: Optional[int] = None
    word_id: Optional[int] = None
    text: str = ""
