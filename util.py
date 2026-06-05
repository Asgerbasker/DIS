import Stemmer
import re


_TOKEN_PATTERN = re.compile(r"[\s\W_]+")
_STEMMER = Stemmer.Stemmer("english")

# Normalize a string by splitting it on all special characters, determined by a regex, and then stemming it
def normalize(value: str | None) -> str:
    if not value:
        return ""

    tokens = _TOKEN_PATTERN.split(value.lower().strip())
    if not tokens:
        return ""

    return " ".join(_STEMMER.stemWord(token) for token in tokens if token)
