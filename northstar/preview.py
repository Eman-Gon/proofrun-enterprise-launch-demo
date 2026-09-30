"""Preview CSV onboarding without writing customer records."""

import csv
import io

from .customers import import_customer

MAX_ROWS = 100


def preview_import(payload):
    """Return row outcomes, rejecting unreadable files and excessive batches."""
    if not isinstance(payload, dict) or not isinstance(payload.get("csv"), str):
        raise ValueError("invalid_csv")
    try:
        reader = csv.DictReader(io.StringIO(payload["csv"], newline=""), strict=True)
        if reader.fieldnames != ["customer_id", "name"]:
            raise ValueError("invalid_csv")
        records = []
        for row in reader:
            if len(records) == MAX_ROWS:
                raise ValueError("invalid_csv")
            records.append(row)
    except csv.Error as exc:
        raise ValueError("invalid_csv") from exc
    if not records:
        raise ValueError("invalid_csv")

    rows = []
    seen_ids = set()
    ready = 0
    for row_number, record in enumerate(records, start=2):
        result = {"row": row_number, "status": "rejected"}
        try:
            if None in record:
                raise ValueError("invalid_customer")
            customer = import_customer(record)
        except ValueError:
            result["error"] = "invalid_customer"
        else:
            if customer["customer_id"] in seen_ids:
                result["error"] = "duplicate_id"
            else:
                seen_ids.add(customer["customer_id"])
                result.update(status="ready", customer=customer)
                ready += 1
        rows.append(result)
    return {"total": len(rows), "ready": ready, "rejected": len(rows) - ready, "rows": rows}
