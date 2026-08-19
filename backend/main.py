from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import math
from backend.database import get_connection
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SLA Monitoring API",
    description="API for SLA monitoring and health-check logs",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health_check():

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT 1;"
        )

        cursor.fetchone()

        cursor.close()
        connection.close()

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "message": "SLA Monitoring API",
        "status": "running",
        "docs": "/docs"
    }


# =========================================================
# SLA SUMMARY
# =========================================================

@app.get("/api/summary")
def get_summary():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        query = """
            SELECT
                COUNT(*) AS total_slots,

                COUNT(*) FILTER (
                    WHERE slot_status = 'available'
                ) AS available_slots,

                COUNT(*) FILTER (
                    WHERE slot_status = 'failed'
                ) AS failed_slots,

                COUNT(*) FILTER (
                    WHERE slot_status = 'missing'
                ) AS missing_slots

            FROM sla_slots;
        """

        cursor.execute(query)

        row = cursor.fetchone()

        if row is None:
            return {
                "total_slots": 0,
                "available_slots": 0,
                "failed_slots": 0,
                "missing_slots": 0,
                "availability_percent": 0,
                "sla_target_percent": 99.9
            }

        total = row[0]
        available = row[1]
        failed = row[2]
        missing = row[3]

        availability = (
            available / total * 100
            if total > 0
            else 0
        )

        return {
            "total_slots": total,
            "available_slots": available,
            "failed_slots": failed,
            "missing_slots": missing,
            "availability_percent": round(
                availability,
                4
            ),
            "sla_target_percent": 99.9,
            "sla_status": (
                "MET"
                if availability >= 99.9
                else "BREACHED"
            )
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# SERVICE METRICS
# =========================================================

@app.get("/api/services")
def get_services():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        query = """
            SELECT
                service_id,

                COUNT(*) AS expected_slots,

                COUNT(*) FILTER (
                    WHERE slot_status = 'available'
                ) AS available_slots,

                COUNT(*) FILTER (
                    WHERE slot_status = 'failed'
                ) AS failed_slots,

                COUNT(*) FILTER (
                    WHERE slot_status = 'missing'
                ) AS missing_slots

            FROM sla_slots

            GROUP BY service_id

            ORDER BY service_id;
        """

        cursor.execute(query)

        rows = cursor.fetchall()

        services = []

        for row in rows:

            (
                service_id,
                expected,
                available,
                failed,
                missing
            ) = row

            availability = (
                available / expected * 100
                if expected > 0
                else 0
            )

            services.append({

                "service_id": service_id,

                "expected_slots": expected,

                "available_slots": available,

                "failed_slots": failed,

                "missing_slots": missing,

                "availability_percent": round(
                    availability,
                    4
                ),

                "sla_target_percent": 99.9,

                "sla_status": (
                    "MET"
                    if availability >= 99.9
                    else "BREACHED"
                )
            })

        return services

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()

# =========================================================
# LOGS
# =========================================================

@app.get("/api/logs")
def get_logs(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000)
):

    connection = None
    cursor = None

    try:

        # -------------------------------------------------
        # DATABASE CONNECTION
        # -------------------------------------------------

        connection = get_connection()
        cursor = connection.cursor()

        # -------------------------------------------------
        # BASE QUERY
        # -------------------------------------------------

        query = """
            SELECT
                service_id,
                timestamp_utc,
                agent,
                region,
                status_code,
                latency_ms,
                source_file
            FROM monitoring_logs
            WHERE 1 = 1
        """

        parameters = []

        # -------------------------------------------------
        # START DATE
        # -------------------------------------------------

        if start_date:

            query += """
                AND timestamp_utc >= %s::date
            """

            parameters.append(start_date)

        # -------------------------------------------------
        # END DATE
        # -------------------------------------------------

        if end_date:

            query += """
                AND timestamp_utc <
                    (%s::date + INTERVAL '1 day')
            """

            parameters.append(end_date)

        # -------------------------------------------------
        # SERVICE FILTER
        # -------------------------------------------------

        if service_id:

            query += """
                AND service_id = %s
            """

            parameters.append(service_id)

        # -------------------------------------------------
        # ORDER + LIMIT
        # -------------------------------------------------

        query += """
            ORDER BY timestamp_utc DESC
            LIMIT %s
        """

        parameters.append(limit)

        # -------------------------------------------------
        # EXECUTE QUERY
        # -------------------------------------------------

        cursor.execute(
            query,
            parameters
        )

        rows = cursor.fetchall()

        # -------------------------------------------------
        # BUILD RESPONSE
        # -------------------------------------------------

        logs = []

        for row in rows:

            # ---------------------------------------------
            # Handle latency
            # ---------------------------------------------

            latency = row[5]

            if latency is None:

                latency_value = None

            else:

                latency_value = float(latency)

                if (
                    math.isnan(latency_value)
                    or math.isinf(latency_value)
                ):

                    latency_value = None

            # ---------------------------------------------
            # Handle timestamp
            # ---------------------------------------------

            if row[1] is not None:

                timestamp_value = row[1].isoformat()

            else:

                timestamp_value = None

            # ---------------------------------------------
            # Add record
            # ---------------------------------------------

            logs.append({

                "service_id": row[0],

                "timestamp_utc": timestamp_value,

                "agent": row[2],

                "region": row[3],

                "status_code": row[4],

                "latency_ms": latency_value,

                "source_file": row[6]

            })

        # -------------------------------------------------
        # RETURN RESPONSE
        # -------------------------------------------------

        return {
            "count": len(logs),
            "logs": logs
        }

    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # =====================================================
    # CLOSE DATABASE CONNECTION
    # =====================================================

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()