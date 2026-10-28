import os

from pymongo import MongoClient
from pymongo.database import Database

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://root:root@localhost:27017/?directConnection=true&authSource=admin",
)
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "testai")

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
database = client[MONGODB_DATABASE]


def connect_to_mongodb() -> Database:
    client.admin.command("ping")
    return database
