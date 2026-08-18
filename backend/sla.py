from pathlib import Path
import pandas as pd


# =========================================================
# CONFIGURATION
# =========================================================

SLA_TARGET = 99.9
SLOT_FREQUENCY = "15min"

DATA_DIR = (
    Path(__file__).resolve().parent.parent / "data"
)


# =========================================================
# LOAD DATA
# =========================================================

def load_all_data():
    """
    Load all CSV files from the data directory.
    """

    files = sorted(DATA_DIR.glob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {DATA_DIR}"
        )

    frames = []

    print(f"\nCSV files found: {len(files)}")

    for file in files:

        print(f"Loading: {file.name}")

        df = pd.read_csv(file)

        # Keep source information
        df["source_file"] = file.name

        frames.append(df)

    combined = pd.concat(
        frames,
        ignore_index=True
    )

    return combined


# =========================================================
# NORMALIZE TIMESTAMP
# =========================================================

def normalize_timestamps(df):

    df = df.copy()

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
        errors="coerce"
    )

    return df


# =========================================================
# NORMALIZE LATENCY
# =========================================================

def normalize_latency(df):

    df = df.copy()

    df["latency"] = pd.to_numeric(
        df["latency"],
        errors="coerce"
    )

    df["latency_ms"] = df["latency"]

    seconds_mask = (
        df["latency_unit"]
        .astype(str)
        .str.lower()
        .eq("s")
    )

    df.loc[
        seconds_mask,
        "latency_ms"
    ] = (
        df.loc[
            seconds_mask,
            "latency"
        ] * 1000
    )

    return df


# =========================================================
# VALIDATE HTTP STATUS
# =========================================================

def validate_status(df):

    df = df.copy()

    status = pd.to_numeric(
        df["status_code"],
        errors="coerce"
    )

    df["status_valid"] = (
        status.between(100, 599)
    )

    return df


# =========================================================
# CLEAN DATA
# =========================================================

def clean_data(df):

    df = df.copy()

    # Remove records with invalid timestamps
    df = df[
        df["timestamp_utc"].notna()
    ].copy()

    # Remove exact duplicate observations
    duplicate_columns = [
        "service_id",
        "service_name",
        "timestamp_utc",
        "status_code",
        "latency_ms",
        "agent",
        "region",
    ]

    duplicate_columns = [
        column
        for column in duplicate_columns
        if column in df.columns
    ]

    before = len(df)

    df = df.drop_duplicates(
        subset=duplicate_columns
    ).copy()

    removed = before - len(df)

    print("\n--- Cleaning ---")
    print(
        f"Exact duplicate records removed: {removed:,}"
    )

    return df


# =========================================================
# CREATE EXPECTED TIMELINE
# =========================================================

def create_expected_timeline(df):

    start = df["timestamp_utc"].min()
    end = df["timestamp_utc"].max()

    start = start.floor(SLOT_FREQUENCY)
    end = end.floor(SLOT_FREQUENCY)

    timestamps = pd.date_range(
        start=start,
        end=end,
        freq=SLOT_FREQUENCY,
        tz="UTC"
    )

    services = (
        df["service_id"]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    expected = pd.MultiIndex.from_product(
        [
            services,
            timestamps
        ],
        names=[
            "service_id",
            "timestamp_utc"
        ]
    ).to_frame(index=False)

    return expected


# =========================================================
# AGGREGATE OBSERVATIONS
# =========================================================

def aggregate_observations(df):

    data = df.copy()

    # Align timestamp to 15-minute slot
    data["timestamp_utc"] = (
        pd.to_datetime(
            data["timestamp_utc"],
            utc=True,
            errors="coerce"
        )
        .dt.floor(SLOT_FREQUENCY)
    )

    status = pd.to_numeric(
        data["status_code"],
        errors="coerce"
    )

    data["status_valid"] = (
        status.between(100, 599)
    )

    data["is_success"] = (
        status.between(200, 299)
    )

    grouped = (
        data
        .groupby(
            [
                "service_id",
                "timestamp_utc"
            ],
            as_index=False
        )
        .agg(
            observed_records=(
                "service_id",
                "size"
            ),

            agent_count=(
                "agent",
                "nunique"
            ),

            valid_observations=(
                "status_valid",
                "sum"
            ),

            successful_observations=(
                "is_success",
                "sum"
            ),

            invalid_observations=(
                "status_valid",
                lambda x: (~x).sum()
            ),
        )
    )

    grouped["failed_observations"] = (
        grouped["valid_observations"]
        - grouped["successful_observations"]
    )

    # -----------------------------------------------------
    # SLA classification
    # -----------------------------------------------------

    grouped["slot_status"] = "missing"

    # Any valid failure = FAILED
    grouped.loc[
        (
            grouped["valid_observations"] > 0
        )
        &
        (
            grouped["failed_observations"] > 0
        ),
        "slot_status"
    ] = "failed"

    # At least one valid observation and
    # no failures = AVAILABLE
    grouped.loc[
        (
            grouped["valid_observations"] > 0
        )
        &
        (
            grouped["failed_observations"] == 0
        ),
        "slot_status"
    ] = "available"

    return grouped


# =========================================================
# BUILD SLA SLOTS
# =========================================================

def build_slot_status(df):

    print(
        "\nCreating expected 15-minute timeline..."
    )

    expected = create_expected_timeline(df)

    print(
        f"Expected slots generated: "
        f"{len(expected):,}"
    )

    observed = aggregate_observations(df)

    result = expected.merge(
        observed,
        on=[
            "service_id",
            "timestamp_utc"
        ],
        how="left"
    )

    # No observation = MISSING
    result["slot_status"] = (
        result["slot_status"]
        .fillna("missing")
    )

    count_columns = [
        "observed_records",
        "agent_count",
        "valid_observations",
        "successful_observations",
        "invalid_observations",
        "failed_observations",
    ]

    for column in count_columns:

        result[column] = (
            result[column]
            .fillna(0)
            .astype(int)
        )

    return result


# =========================================================
# SLA METRICS
# =========================================================

def calculate_sla_metrics(slots):

    metrics = []

    for service_id, group in slots.groupby(
        "service_id"
    ):

        expected = len(group)

        available = (
            group["slot_status"]
            .eq("available")
            .sum()
        )

        failed = (
            group["slot_status"]
            .eq("failed")
            .sum()
        )

        missing = (
            group["slot_status"]
            .eq("missing")
            .sum()
        )

        availability = (
            available / expected * 100
            if expected > 0
            else 0
        )

        sla_status = (
            "MET"
            if availability >= SLA_TARGET
            else "BREACHED"
        )

        metrics.append({

            "service_id": service_id,

            "expected_slots": expected,

            "available_slots": int(
                available
            ),

            "failed_slots": int(
                failed
            ),

            "missing_slots": int(
                missing
            ),

            "availability_percent": round(
                availability,
                4
            ),

            "sla_target_percent": SLA_TARGET,

            "sla_status": sla_status

        })

    return pd.DataFrame(metrics)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("=" * 70)
    print("SLA CALCULATION")
    print("=" * 70)

    # -----------------------------------------------------
    # 1. LOAD
    # -----------------------------------------------------

    df = load_all_data()

    print(
        f"\nRaw records: {len(df):,}"
    )

    # -----------------------------------------------------
    # 2. TIMESTAMP NORMALIZATION
    # -----------------------------------------------------

    df = normalize_timestamps(df)

    # -----------------------------------------------------
    # 3. LATENCY NORMALIZATION
    # -----------------------------------------------------

    df = normalize_latency(df)

    # -----------------------------------------------------
    # 4. STATUS VALIDATION
    # -----------------------------------------------------

    df = validate_status(df)

    # -----------------------------------------------------
    # 5. CLEANING
    # -----------------------------------------------------

    df = clean_data(df)

    print(
        f"Records after cleaning: "
        f"{len(df):,}"
    )

    # -----------------------------------------------------
    # 6. BUILD SLA SLOTS
    # -----------------------------------------------------

    slots = build_slot_status(df)

    print(
        f"\nTotal expected SLA slots: "
        f"{len(slots):,}"
    )

    # -----------------------------------------------------
    # 7. SLOT SUMMARY
    # -----------------------------------------------------

    print("\nSLOT STATUS SUMMARY")
    print("-" * 70)

    summary = (
        slots["slot_status"]
        .value_counts()
        .rename_axis("slot_status")
        .reset_index(
            name="count"
        )
    )

    print(
        summary.to_string(
            index=False
        )
    )

    # -----------------------------------------------------
    # 8. SLA METRICS
    # -----------------------------------------------------

    metrics = calculate_sla_metrics(
        slots
    )

    print("\nSERVICE SLA METRICS")
    print("-" * 70)

    print(
        metrics.to_string(
            index=False
        )
    )

    # -----------------------------------------------------
    # 9. COMPLETE
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("SLA CALCULATION COMPLETE")
    print("=" * 70)