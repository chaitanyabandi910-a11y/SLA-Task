from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

REQUIRED_COLUMNS = [
    "service_id",
    "service_name",
    "timestamp",
    "status_code",
    "latency",
    "latency_unit",
    "agent",
    "region",
]

VALID_LATENCY_UNITS = {"ms", "s"}

VALID_HTTP_STATUS_MIN = 100
VALID_HTTP_STATUS_MAX = 599


# ============================================================
# LOAD ONE CSV FILE
# ============================================================

def load_data(file_path):
    """
    Load one CSV file.

    The file path is supplied by ingest.py.
    The original CSV file is never modified.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if file_path.suffix.lower() != ".csv":
        raise ValueError(
            f"Expected a CSV file, got: {file_path}"
        )

    df = pd.read_csv(file_path)

    # Store the original filename for traceability.
    df["source_file"] = file_path.name

    return df


# ============================================================
# COLUMN VALIDATION
# ============================================================

def validate_columns(df):
    """
    Check whether all required columns exist.
    """

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )


# ============================================================
# MISSING VALUE VALIDATION
# ============================================================

def validate_missing_values(df):
    """
    Report missing values in important columns.
    """

    print("\n--- Missing values ---")

    for column in REQUIRED_COLUMNS:

        count = df[column].isna().sum()

        print(
            f"{column:15} : {count:,}"
        )


# ============================================================
# HTTP STATUS VALIDATION
# ============================================================

def validate_status_codes(df):
    """
    Detect invalid HTTP status codes.

    Valid HTTP status codes are between 100 and 599.
    """

    status_numeric = pd.to_numeric(
        df["status_code"],
        errors="coerce"
    )

    invalid = (
        status_numeric.isna()
        |
        (status_numeric < VALID_HTTP_STATUS_MIN)
        |
        (status_numeric > VALID_HTTP_STATUS_MAX)
    )

    print("\n--- Invalid HTTP status codes ---")

    print(
        f"Invalid records: {invalid.sum():,}"
    )

    if invalid.sum() > 0:

        print(
            df.loc[
                invalid,
                [
                    "service_id",
                    "timestamp",
                    "status_code"
                ]
            ]
            .head(10)
            .to_string(index=False)
        )


# ============================================================
# LATENCY VALIDATION
# ============================================================

def validate_latency(df):
    """
    Detect invalid latency values and units.
    """

    latency_numeric = pd.to_numeric(
        df["latency"],
        errors="coerce"
    )

    negative_latency = (
        latency_numeric < 0
    )

    invalid_units = ~df[
        "latency_unit"
    ].isin(VALID_LATENCY_UNITS)

    missing_latency = (
        latency_numeric.isna()
    )

    print("\n--- Latency validation ---")

    print(
        f"Negative latency: "
        f"{negative_latency.sum():,}"
    )

    print(
        f"Invalid latency units: "
        f"{invalid_units.sum():,}"
    )

    print(
        f"Missing/non-numeric latency: "
        f"{missing_latency.sum():,}"
    )


# ============================================================
# DUPLICATE VALIDATION
# ============================================================

def validate_duplicates(df):
    """
    Detect exact duplicate rows.
    """

    duplicates = df.duplicated()

    print("\n--- Duplicate validation ---")

    print(
        f"Duplicate rows: "
        f"{duplicates.sum():,}"
    )


# ============================================================
# SERVICE VALIDATION
# ============================================================

def validate_services(df):
    """
    Check whether a service_id maps to
    multiple service names.
    """

    mapping = (
        df[
            [
                "service_id",
                "service_name"
            ]
        ]
        .drop_duplicates()
    )

    inconsistent = (
        mapping
        .groupby("service_id")
        .size()
    )

    inconsistent = inconsistent[
        inconsistent > 1
    ]

    print("\n--- Service validation ---")

    print(
        f"Services with multiple names: "
        f"{len(inconsistent)}"
    )

    if len(inconsistent) > 0:

        print(
            inconsistent.to_string()
        )


# ============================================================
# AGENT VALIDATION
# ============================================================

def validate_agents(df):
    """
    Display monitoring agents.
    """

    print("\n--- Agents ---")

    print(
        df["agent"]
        .value_counts(dropna=False)
        .to_string()
    )


# ============================================================
# REGION VALIDATION
# ============================================================

def validate_regions(df):
    """
    Display monitoring regions.
    """

    print("\n--- Regions ---")

    print(
        df["region"]
        .value_counts(dropna=False)
        .to_string()
    )


# ============================================================
# RUN ALL VALIDATIONS
# ============================================================

def run_validation(df):

    print("=" * 60)
    print("SLA DATA VALIDATION")
    print("=" * 60)

    print(
        f"\nTotal records: {len(df):,}"
    )

    # Required columns must exist before
    # checking individual columns.
    validate_columns(df)

    validate_missing_values(df)

    validate_status_codes(df)

    validate_latency(df)

    validate_duplicates(df)

    validate_services(df)

    validate_agents(df)

    validate_regions(df)

    print(
        "\n" + "=" * 60
    )

    print(
        "VALIDATION COMPLETE"
    )

    print(
        "=" * 60
    )


# ============================================================
# DIRECT SCRIPT EXECUTION
# ============================================================

if __name__ == "__main__":

    # Project root
    project_root = (
        Path(__file__).resolve().parent.parent
    )

    # data/ directory
    data_dir = project_root / "data"

    # Find all CSV files
    files = sorted(
        data_dir.glob("*.csv")
    )

    if not files:

        raise FileNotFoundError(
            f"No CSV files found in {data_dir}"
        )

    print(
        f"Found {len(files)} CSV files."
    )

    # Validate each file separately.
    for file_path in files:

        print(
            "\n\n"
            + "#" * 70
        )

        print(
            f"FILE: {file_path.name}"
        )

        print(
            "#" * 70
        )

        df = load_data(file_path)

        run_validation(df)