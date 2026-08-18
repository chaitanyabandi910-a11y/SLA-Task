import os
import psycopg2
from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set in .env"
    )


try:
    connection = psycopg2.connect(
        DATABASE_URL
    )

    print("Database connection successful!")

    cursor = connection.cursor()

    cursor.execute(
        "SELECT version();"
    )

    version = cursor.fetchone()

    print("PostgreSQL version:")
    print(version[0])

    cursor.close()
    connection.close()

except Exception as e:

    print("Database connection failed:")
    print(e)