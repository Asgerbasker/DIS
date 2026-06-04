from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container
from flask import current_app
from typing import Any, Tuple
import docker
import logging
import psycopg2
from entities import *
import pandas as pd
from tqdm import tqdm
from util import normalize

logger = logging.getLogger(__name__)


def setup_db() -> Container:
    container = start_postgres_container()
    create_db_schema()
    data = load_kaggle_data()
    insert_data_into_db(data)
    return container


def start_postgres_container() -> Container:
    config = current_app.config
    container_name = config["CONTAINER_NAME"]

    logger.info("Checking for Postgres container named %s", container_name)
    client = docker.from_env()

    try:
        container = client.containers.get(container_name)
        container.reload()
        logger.info("Found existing container %s with status %s", container_name, container.status)

        if container.status != "running":
            logger.info("Starting existing container %s", container_name)
            container.start()
            container.reload()
            logger.info("Container %s is now running", container_name)
        else:
            logger.info("Container %s is already running", container_name)

        return container
    except NotFound:
        logger.info("No container named %s exists yet; creating one", container_name)
    except (APIError, DockerException) as exc:
        raise RuntimeError(f"Failed to inspect container {container_name}") from exc

    try:
        container = client.containers.run(
            "postgres:16",
            name=container_name,
            detach=True,
            environment={
                "POSTGRES_USER": config["POSTGRES_USER"],
                "POSTGRES_PASSWORD": config["POSTGRES_PASSWORD"],
                "POSTGRES_DB": config["POSTGRES_DB"],
            },
            ports={"5432/tcp": ("127.0.0.1", config["POSTGRES_PORT"])},
        )
        logger.info("Started new container %s from image postgres:16", container.short_id)
        return container
    except (APIError, DockerException) as exc:
        raise RuntimeError(f"Failed to start container {container_name}") from exc

def create_db_schema() -> None:
    config = current_app.config

    logger.info("Setting up database schema in Postgres container %s", config["CONTAINER_NAME"])
    connection = psycopg2.connect(
        host="localhost",
        port=config["POSTGRES_PORT"],
        dbname=config["POSTGRES_DB"],
        user=config["POSTGRES_USER"],
        password=config["POSTGRES_PASSWORD"],
    )

    try:
        with connection, connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS relation")
            cursor.execute("DROP TABLE IF EXISTS example")
            cursor.execute("DROP TABLE IF EXISTS word")
            cursor.execute(
                """
                CREATE TABLE word (
                    "Id" SERIAL PRIMARY KEY,
                    "Description" TEXT,
                    "PartOfSpeech" INTEGER,
                    "Stemmed" TEXT,
                    "RawForm" TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE example (
                    "Id" SERIAL PRIMARY KEY,
                    "WordId" INTEGER NOT NULL REFERENCES word("Id") ON DELETE CASCADE,
                    "Text" TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE relation (
                    "WId1" INTEGER NOT NULL REFERENCES word("Id") ON DELETE CASCADE,
                    "WId2" INTEGER NOT NULL REFERENCES word("Id") ON DELETE CASCADE,
                    "Type" INTEGER NOT NULL,
                    PRIMARY KEY ("WId1", "WId2", "Type")
                )
                """
            )
        logger.info("Schema is ready")
    finally:
        connection.close()

def load_kaggle_data() -> Tuple[list[Word], list[WordRelation]]:
    df_all = pd.concat([
        __load_adjectives(),
        __load_adverbs(),
        __load_nouns(),
        __load_verbs()
    ], ignore_index=True)
    words = []
    example_id = 0

    for word_id, (_, row) in enumerate(df_all.iterrows()):
        examples = []
        for ex in row["Combined"]:
            examples.append(Example(example_id, word_id, ex))
            example_id += 1

        normalized_word = normalize(row["Word"])
        words.append(Word(
            word_id,
            row["Definition"],
            row["POS"],
            normalized_word,
            row["Word"],
            examples,
            [],
        ))

    logger.info("Loaded %d words from Kaggle dataset", len(words))
    relations = __load_relations({word.raw_form: word.id for word in words}  )
    return words, relations


def insert_data_into_db(data: Tuple[list[Word], list[WordRelation]]) -> None:
    words, relations = data
    config = current_app.config
    connection = psycopg2.connect(
        host="localhost",
        port=config["POSTGRES_PORT"],
        dbname=config["POSTGRES_DB"],
        user=config["POSTGRES_USER"],
        password=config["POSTGRES_PASSWORD"],
    )

    try:
        with connection, connection.cursor() as cursor:
                for word in tqdm(words, desc="Inserting words", total=len(words)):
                    cursor.execute(
                        """
                        INSERT INTO word ("Id", "Description", "PartOfSpeech", "Stemmed", "RawForm")
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (word.id, word.description, word.part_of_speech, word.stemmed, word.raw_form),
                    )

                    for example in word.examples:
                        cursor.execute(
                            """
                            INSERT INTO example ("Id", "WordId", "Text")
                            VALUES (%s, %s, %s)
                            """,
                            (example.id, example.word_id, example.text),
                        )

        if relations:
            __insert_relations(connection, relations)

        logger.info("Inserted %d words, %d examples, and %d relations", len(words), sum(len(word.examples) for word in words), len(relations))
    finally:
        connection.close()


def __insert_relations(connection: psycopg2.extensions.connection, relations: list[WordRelation]) -> None:
    if not relations:
        return

    with connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO relation ("WId1", "WId2", "Type")
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                [
                    (relation.word_id_1, relation.word_id_2, int(relation.relation_type))
                    for relation in relations
                ],
            )

def __load_adjectives() -> list[Word]:
    df = pd.read_csv("dataset/WordnetAdjectives.csv"
    ).dropna(subset=["Word", "Definition"]
    ).drop(columns=["Count"])
    df['Combined'] = df.apply(
        lambda row: [x for x in [row['Senses']] + [row[f'Example {i}'] for i in range(1, 5)] if pd.notna(x)],
        axis=1)
    df['POS'] = PartOfSpeech.ADJECTIVE
    return df.drop(columns=['Senses', 'Example 1', 'Example 2', 'Example 3', 'Example 4'])

def __load_adverbs() -> pd.DataFrame:
    df = pd.read_csv("dataset/WordnetAdverbs.csv"
    ).dropna(subset=["Word", "Definition"]
    ).drop(columns=["Count"])
    df['Combined'] = df.apply(
        lambda row: [x for x in [row['Senses']] + [row["Example"]] if pd.notna(x)],
        axis=1
    )
    df['POS'] = PartOfSpeech.ADVERB
    df = df.drop(columns=['Senses', 'Example'])
    return df

def __load_nouns() -> pd.DataFrame:
    df = pd.read_csv("dataset/WordnetNouns.csv"
    ).dropna(subset=["Word", "Definition"]
    ).drop(columns=["Count", "POS"])
    df['Combined'] = [[] for _ in range(len(df))]
    df['POS'] = PartOfSpeech.NOUN
    return df

def __load_verbs() -> pd.DataFrame:
    df = pd.read_csv("dataset/WordnetVerbs.csv"
    ).dropna(subset=["Word", "Definition"]
    ).drop(columns=["Count", "Sense"])
    df['Combined'] = df.apply(
        lambda row: [x for x in [row[f'Example {i}'] for i in range(1, 3)] if pd.notna(x)],
        axis=1
    )
    df = df.drop(columns=['Example 1', 'Example 2'])
    df['POS'] = PartOfSpeech.VERB
    return df

def __load_relations(word_id_map: dict[str, int]) -> list[WordRelation]:
    logger.info("Loading word relations")
    syn_df = pd.read_csv("dataset/WordnetSynonyms.csv"
        ).dropna(subset=["Word"]
        ).drop(columns=["Count"]
        ).groupby('Word', as_index=False, sort=False).agg({
            'Synonyms': lambda s: ';'.join(s.dropna().astype(str))
        }
        ).rename(columns={'Synonyms': 'RelatedWords'})
    syn_df["Type"] = "Synonym"
    logger.info("Loaded %d synonyms", len(syn_df))
    ant_df = pd.read_csv("dataset/WordnetAntonyms.csv"
        ).dropna(subset=["Word"]
        ).drop(columns=["Count"]
        ).groupby('Word', as_index=False, sort=False).agg({
            'Antonyms': lambda s: ';'.join(s.dropna().astype(str))
        }
        ).rename(columns={'Antonyms': 'RelatedWords'})
    ant_df["Type"] = "Antonym"
    logger.info("Loaded %d antonyms", len(ant_df))
    all_rels = pd.concat([ant_df, syn_df], ignore_index=True)
    relation_tuples = []
    some_not_exist = False

    for _, row in tqdm(all_rels.iterrows(), total=len(all_rels), desc="Processing relations"):
        word = row["Word"]
        if word not in word_id_map:
            some_not_exist = True
            continue
        related_words = row["RelatedWords"].split(';')
        for related_word in related_words:
            if related_word not in word_id_map:
                some_not_exist = True
                continue

            type = RelationType.SYNONYM if row["Type"] == "Synonym" else RelationType.ANTONYM
            relation_tuples.append(WordRelation(word_id_map[word], word_id_map[related_word], type))

    if some_not_exist:
        logger.warning("Some relations were skipped because the word or related word was not found in the main dataset")

    logger.info("Processed %d relations", len(relation_tuples))
    return relation_tuples
