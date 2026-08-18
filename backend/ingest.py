from pathlib import Path
import pandas as pd

from validation import load_data
from normalization import normalize_data
from cleaning import clean_data
from sla import build_slot_status, calculate_sla_metrics

from db import (
    create_upload,
    update_upload,
    insert_services,
    insert_monitoring_logs,
    insert_sla_slots,
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DATA_DIR = Path("data")


# ---------------------------------------------------------
# Find CSV files
# ---------------------------------------------------------

def find_csv_files():

    files = sorted(DATA_DIR.glob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {DATA_DIR}"
        )

    return files


# ---------------------------------------------------------
# Process one CSV
# ---------------------------------------------------------

def process_file(file_path):

    print("\n" + "=" * 70)
    print(f"PROCESSING: {file_path.name}")
    print("=" * 70)

    # -----------------------------------------------------
    # 1. Load
    # -----------------------------------------------------

    df = load_data(file_path)

    total_rows = len(df)

    print(
        f"Raw rows: {total_rows:,}"
    )

    # -----------------------------------------------------
    # 2. Normalize
    # -----------------------------------------------------

    normalized = normalize_data(df)

    # -----------------------------------------------------
    # 3. Clean
    # -----------------------------------------------------

    cleaned = clean_data(normalized)

    # -----------------------------------------------------
    # 4. Calculate cleaning statistics
    # -----------------------------------------------------

    duplicate_rows = (
        total_rows - len(
            normalized.drop_duplicates()
        )
    )

    invalid_status_rows = int(
        (~cleaned["status_valid"]).sum()
    )

    invalid_latency_rows = int(
        (~cleaned["latency_valid"]).sum()
    )

    # -----------------------------------------------------
    # 5. Create upload record
    # -----------------------------------------------------

    upload_id = create_upload(
        filename=file_path.name,
        total_rows=total_rows,
    )

    print(
        f"Upload ID: {upload_id}"
    )

    # -----------------------------------------------------
    # 6. Add source filename
    # -----------------------------------------------------

    cleaned = cleaned.copy()

    cleaned["source_file"] = file_path.name

    # -----------------------------------------------------
    # 7. Insert services
    # -----------------------------------------------------

    insert_services(cleaned)

    # -----------------------------------------------------
    # 8. Insert monitoring logs
    # -----------------------------------------------------

    insert_monitoring_logs(
        cleaned,
        upload_id,
    )

    # -----------------------------------------------------
    # 9. Build SLA slots
    # -----------------------------------------------------

    slots = build_slot_status(
        cleaned
    )

    # -----------------------------------------------------
    # 10. Insert SLA slots
    # -----------------------------------------------------

    insert_sla_slots(
        slots,
        upload_id,
    )

    # -----------------------------------------------------
    # 11. Calculate metrics
    # -----------------------------------------------------

    metrics = calculate_sla_metrics(
        slots
    )

    # -----------------------------------------------------
    # 12. Update upload record
    # -----------------------------------------------------

    update_upload(
        upload_id=upload_id,
        duplicate_rows=duplicate_rows,
        invalid_status_rows=invalid_status_rows,
        invalid_latency_rows=invalid_latency_rows,
        cleaned_rows=len(cleaned),
        status="completed",
    )

    print(
        f"Inserted monitoring records: "
        f"{len(cleaned):,}"
    )

    print(
        f"Generated SLA slots: "
        f"{len(slots):,}"
    )

    print("\nSLA metrics:")

    print(
        metrics.to_string(index=False)
    )

    return metrics


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("SLA MONITORING DATA INGESTION")
    print("=" * 70)

    files = find_csv_files()

    print(
        f"\nCSV files found: {len(files)}"
    )

    for file_path in files:

        try:

            process_file(file_path)

        except Exception as e:

            print(
                f"\nERROR processing "
                f"{file_path.name}:"
            )

            print(e)

    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()