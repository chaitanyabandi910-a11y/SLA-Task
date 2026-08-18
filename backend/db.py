import os

import psycopg2
from psycopg2.extras import execute_values

from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set in .env"
    )


def get_connection():
    """
    Create a PostgreSQL database connection.
    """

    return psycopg2.connect(
        DATABASE_URL
    )


# =========================================================
# Upload
# =========================================================

def create_upload(
    filename,
    total_rows
):
    """
    Create an upload record and return its ID.
    """

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO uploads (
                    filename,
                    total_rows,
                    status
                )
                VALUES (%s, %s, %s)
                RETURNING upload_id;
                """,
                (
                    filename,
                    total_rows,
                    "processing",
                ),
            )

            upload_id = cursor.fetchone()[0]

        connection.commit()

        return upload_id

    finally:

        connection.close()


# =========================================================
# Update upload
# =========================================================

def update_upload(
    upload_id,
    duplicate_rows,
    invalid_status_rows,
    invalid_latency_rows,
    cleaned_rows,
    status
):
    """
    Update upload processing statistics.
    """

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE uploads
                SET
                    duplicate_rows = %s,
                    invalid_status_rows = %s,
                    invalid_latency_rows = %s,
                    cleaned_rows = %s,
                    status = %s
                WHERE upload_id = %s;
                """,
                (
                    duplicate_rows,
                    invalid_status_rows,
                    invalid_latency_rows,
                    cleaned_rows,
                    status,
                    upload_id,
                ),
            )

        connection.commit()

    finally:

        connection.close()


# =========================================================
# Services
# =========================================================

def insert_services(df):
    """
    Insert unique services.
    """

    services = (
        df[
            [
                "service_id",
                "service_name"
            ]
        ]
        .drop_duplicates()
        .values
        .tolist()
    )

    if not services:
        return

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            execute_values(
                cursor,
                """
                INSERT INTO services (
                    service_id,
                    service_name
                )
                VALUES %s
                ON CONFLICT (service_id)
                DO UPDATE SET
                    service_name =
                    EXCLUDED.service_name;
                """,
                services,
            )

        connection.commit()

    finally:

        connection.close()


# =========================================================
# Monitoring logs
# =========================================================

def insert_monitoring_logs(
    df,
    upload_id
):
    """
    Insert cleaned monitoring records.
    """

    if df.empty:
        return

    records = []

    for _, row in df.iterrows():

        records.append(
            (
                upload_id,
                row["service_id"],
                row["service_name"],
                row["timestamp_utc"],
                row["status_code"],
                row["latency_ms"],
                row["agent"],
                row["region"],
                row.get("source_file"),
                bool(row["status_valid"]),
                bool(row["latency_valid"]),
            )
        )

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            execute_values(
                cursor,
                """
                INSERT INTO monitoring_logs (
                    upload_id,
                    service_id,
                    service_name,
                    timestamp_utc,
                    status_code,
                    latency_ms,
                    agent,
                    region,
                    source_file,
                    status_valid,
                    latency_valid
                )
                VALUES %s;
                """,
                records,
            )

        connection.commit()

    finally:

        connection.close()


# =========================================================
# SLA slots
# =========================================================

def insert_sla_slots(
    df,
    upload_id
):
    """
    Insert calculated SLA slot results.
    """

    if df.empty:
        return

    records = []

    for _, row in df.iterrows():

        records.append(
            (
                upload_id,
                row["service_id"],
                row["timestamp_utc"],
                row["agent_count"],
                row["successful_agents"],
                row["failed_agents"],
                row["observed_records"],
                row["slot_status"],
            )
        )

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            execute_values(
                cursor,
                """
                INSERT INTO sla_slots (
                    upload_id,
                    service_id,
                    timestamp_utc,
                    agent_count,
                    successful_agents,
                    failed_agents,
                    observed_records,
                    slot_status
                )
                VALUES %s
                ON CONFLICT (
                    service_id,
                    timestamp_utc
                )
                DO UPDATE SET
                    upload_id =
                        EXCLUDED.upload_id,
                    agent_count =
                        EXCLUDED.agent_count,
                    successful_agents =
                        EXCLUDED.successful_agents,
                    failed_agents =
                        EXCLUDED.failed_agents,
                    observed_records =
                        EXCLUDED.observed_records,
                    slot_status =
                        EXCLUDED.slot_status;
                """,
                records,
            )

        connection.commit()

    finally:

        connection.close()


# =========================================================
# Test
# =========================================================

if __name__ == "__main__":

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT current_database();"
            )

            database = cursor.fetchone()[0]

            print(
                f"Connected to database: {database}"
            )

    finally:

        connection.close()