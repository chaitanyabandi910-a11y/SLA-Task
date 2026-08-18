from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------
# Load all CSV files
# ---------------------------------------------------------

def load_csv_files():
    files = sorted(DATA_DIR.glob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {DATA_DIR}"
        )

    dataframes = []

    for file in files:
        print(f"Loading: {file.name}")

        df = pd.read_csv(file)
        df["source_file"] = file.name

        dataframes.append(df)

    combined = pd.concat(
        dataframes,
        ignore_index=True
    )

    return combined


# ---------------------------------------------------------
# Profile dataset
# ---------------------------------------------------------

def profile_dataset(df):

    print("\n" + "=" * 60)
    print("SLA MONITORING DATASET PROFILE")
    print("=" * 60)

    print(f"\nTotal rows: {len(df):,}")

    print("\nColumns:")
    for column in df.columns:
        print(f"  - {column}")

    print("\nServices:")
    print(df["service_id"].value_counts())

    print("\nService name mapping:")
    print(
        df[
            ["service_id", "service_name"]
        ]
        .drop_duplicates()
        .sort_values("service_id")
        .to_string(index=False)
    )

    print("\nAgents:")
    print(df["agent"].value_counts())

    print("\nRegions:")
    print(df["region"].value_counts())

    print("\nStatus codes:")
    print(df["status_code"].value_counts().sort_index())

    print("\nLatency units:")
    print(df["latency_unit"].value_counts(dropna=False))

    print("\nMissing values:")
    print(
        df.isna()
        .sum()
        .sort_values(ascending=False)
    )

    print("\nExact duplicate rows:")
    print(df.duplicated().sum())

    print("\nRaw timestamp examples:")
    print(df["timestamp"].head(10).to_string(index=False))

    print("\nDataset profile complete.")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":

    df = load_csv_files()

    profile_dataset(df)