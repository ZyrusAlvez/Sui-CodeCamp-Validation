import csv
from datetime import datetime


def clean(input_file, output_file):
    """Remove duplicate rows by email, keeping the most recent (last) entry."""
    rows = []
    with open(input_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    rows.sort(key=lambda r: datetime.strptime(r["Timestamp"].strip(), "%m/%d/%Y %H:%M:%S"))

    seen = {}
    for row in rows:
        email = row["Email Address"].strip().lower()
        seen[email] = row

    deduped = list(seen.values())

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"[CLEAN] Removed {len(rows) - len(deduped)} duplicates, kept {len(deduped)} rows")
    return output_file
