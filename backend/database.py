import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """
    Create a PostgreSQL database connection.
    """

    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is not set in the .env file"
        )

    return psycopg2.connect(
        DATABASE_URL
    )