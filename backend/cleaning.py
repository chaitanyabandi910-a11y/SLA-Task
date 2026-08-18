import pandas as pd


# ---------------------------------------------------------
# Remove exact duplicates
# ---------------------------------------------------------

def remove_duplicates(df):
    """
    Remove exact duplicate records.

    Records from different agents are NOT considered
    duplicates because the agent is part of the observation.
    """

    before = len(df)

    result = df.drop_duplicates().copy()

    removed = before - len(result)

    print(f"Exact duplicates removed: {removed:,}")

    return result


# ---------------------------------------------------------
# Handle invalid status codes
# ---------------------------------------------------------

def handle_invalid_status(df):
    """
    Mark invalid HTTP status codes.

    We do not silently convert invalid statuses into another
    status code.
    """

    result = df.copy()

    status = pd.to_numeric(
        result["status_code"],
        errors="coerce"
    )

    result["status_valid"] = (
        status.between(100, 599)
    )

    invalid_count = (
        ~result["status_valid"]
    ).sum()

    print(
        f"Invalid status records: {invalid_count:,}"
    )

    return result


# ---------------------------------------------------------
# Handle negative latency
# ---------------------------------------------------------

def handle_negative_latency(df):
    """
    Mark negative latency as invalid.

    We preserve the record for auditability, but mark the
    latency as invalid.
    """

    result = df.copy()

    result["latency_valid"] = (
        result["latency_ms"].isna()
        |
        (result["latency_ms"] >= 0)
    )

    invalid_count = (
        ~result["latency_valid"]
    ).sum()

    print(
        f"Negative latency records: {invalid_count:,}"
    )

    return result


# ---------------------------------------------------------
# Build cleaned dataset
# ---------------------------------------------------------

def clean_data(df):

    result = df.copy()

    # 1. Remove exact duplicates
    result = remove_duplicates(result)

    # 2. Validate HTTP status
    result = handle_invalid_status(result)

    # 3. Validate latency
    result = handle_negative_latency(result)

    return result


# ---------------------------------------------------------
# Create final valid dataset
# ---------------------------------------------------------

def create_valid_dataset(df):

    result = df[
        df["status_valid"]
        &
        df["latency_valid"]
    ].copy()

    return result


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":

    from validation import load_data
    from normalization import normalize_data

    print("=" * 60)
    print("SLA DATA CLEANING")
    print("=" * 60)

    # Load raw data
    df = load_data()

    print(f"\nRaw records: {len(df):,}")

    # Normalize
    normalized = normalize_data(df)

    # Clean
    cleaned = clean_data(normalized)

    print(
        f"\nRecords after duplicate removal: "
        f"{len(cleaned):,}"
    )

    # Create valid subset
    valid = create_valid_dataset(cleaned)

    print(
        f"Fully valid records: "
        f"{len(valid):,}"
    )

    print("\nCleaning complete.")