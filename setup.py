from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container
from flask import current_app
from typing import Any
import docker
import logging
import tempfile
import psycopg2
from entities import *


logger = logging.getLogger(__name__)

def setup_db() -> None:
    container = start_postgres_container()
    create_db_schema()
    data = load_kaggle_data()
    #insert_data_into_db(data)


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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS word (
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
                CREATE TABLE IF NOT EXISTS example (
                    "Id" SERIAL PRIMARY KEY,
                    "WordId" INTEGER NOT NULL REFERENCES word("Id") ON DELETE CASCADE,
                    "Text" TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS relation (
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

def load_kaggle_data() -> Any:
    raise NotImplementedError("This function is not implemented yet")
def insert_data_into_db(data: Any) -> None:
    raise NotImplementedError("This function is not implemented yet")