import os

class Config:
    CONTAINER_NAME = os.environ.get("CONTAINER_NAME", "wordnet-db")
    POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "wordnet")
    POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "8888"))
