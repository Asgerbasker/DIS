from entities.related_word import WordRelation
from entities.part_of_speech import PartOfSpeech
from entities.example import Example
from entities.relation_type import RelationType
from dataclasses import dataclass, field
from typing import Optional
from util import normalize
from typing import Tuple

@dataclass(slots=True)
class Word:
    id: Optional[int] = None
    description: Optional[str] = None
    part_of_speech: Optional[int] = None
    stemmed: Optional[str] = None
    raw_form: Optional[str] = None
    examples: list["Example"] = field(default_factory=list)
    related_words: list["WordRelation"] = field(default_factory=list)

    @staticmethod
    def search_words(query: str, db_connection) -> list["Word"]:
        normalized = normalize(query)
        if not normalized:
            return []
        
        with db_connection, db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT Id, Description, PartOfSpeech, Stemmed, RawForm FROM word
                WHERE Stemmed = %s
                ORDER BY RawForm
                """, (normalized,))
            word_rows = cur.fetchall()

            return [Word(
                id,desc,PartOfSpeech(pos),stem,raw,
                related_words=Word.__find_relations(id, cur),
                examples=Word.__find_examples(id, cur),
            ) for (id,desc,pos,stem,raw) in word_rows]
        
    @staticmethod
    def get_related_words(wordid: int, db_connection) -> list[Tuple[str, RelationType]]:
        with db_connection, db_connection.cursor() as cur:
            relations = Word.__find_relations(wordid, cur)
            related_words = [
                (
                    Word.__get_raw_form(relation.word_id_2, cur), 
                    relation.relation_type)
                for relation in relations
            ]
            return related_words

    @staticmethod
    def __get_raw_form(wordid: int, cursor) -> Optional[str]:
        cursor.execute('SELECT RawForm from word WHERE Id = %s', (wordid,))
        row = cursor.fetchone()
        if not row:
            return None
        return row[0]

    @staticmethod
    def __find_relations(wordid : int, cursor) -> list["WordRelation"]:
        cursor.execute(
            """
            SELECT r.WId1, r.WId2, r.Type
            FROM relation r
            JOIN word w2 ON w2.Id = r.WId2
            WHERE r.WId1 = %s
            ORDER BY w2.RawForm
            """, (wordid,))
        relation_rows = cursor.fetchall()
        return [WordRelation(*row) for row in relation_rows]
    
    @staticmethod
    def __find_examples(wordid: int, cursor) -> list["Example"]:
        cursor.execute(
            """
            SELECT e.Id, e.WordId, e.Text
            FROM example e
            JOIN word w ON w.Id = e.WordId
            WHERE w.Id = %s
            """, (wordid,))
        example_rows = cursor.fetchall()
        return [Example(*row) for row in example_rows]
