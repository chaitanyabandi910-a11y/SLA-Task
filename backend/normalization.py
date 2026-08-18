import pandas as pd


def normalize_timestamps(df):
    """
    Convert all timestamps to UTC.

    Handles:
    - ISO timestamps ending in Z
    - ISO timestamps containing timezone offsets
    - Unix epoch timestamps
    """

    result = df.copy()

    raw = result["timestamp"]

    # First try normal datetime parsing.
    parsed = pd.to_datetime(
        raw,
        errors="coerce",
        utc=True
    )

    # Identify values that were not parsed normally.
    missing = parsed.isna()

    if missing.any():

        numeric_timestamp = pd.to_numeric(
            raw[missing],
            errors="coerce"
        )

        parsed.loc[missing] = pd.to_datetime(
            numeric_timestamp,
            unit="s",
            errors="coerce",
            utc=True
        )

    result["timestamp_utc"] = parsed

    return result


def normalize_latency(df):
    """
    Convert all latency values to milliseconds.
    """

    result = df.copy()

    latency = pd.to_numeric(
        result["latency"],
        errors="coerce"
    )

    result["latency_ms"] = latency

    seconds = result["latency_unit"].eq("s")

    result.loc[
        seconds,
        "latency_ms"
    ] = (
        latency[seconds] * 1000
    )

    return result


def normalize_data(df):

    result = df.copy()

    result = normalize_timestamps(result)

    result = normalize_latency(result)

    return result

#test_normalization if __name__ == "__main__":

    from validation import load_data

    df = load_data()

    cleaned = normalize_data(df)

    print("\nTimestamp examples:")
    print(
        cleaned[
            ["timestamp", "timestamp_utc"]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nLatency examples:")
    print(
        cleaned[
            [
                "latency",
                "latency_unit",
                "latency_ms"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )
    