import argparse
import csv
import hashlib
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


EXPECTED_COLUMNS = [
    "Transaction ID",
    "Customer ID",
    "Category",
    "Item",
    "Price Per Unit",
    "Quantity",
    "Total Spent",
    "Payment Method",
    "Location",
    "Transaction Date",
    "Discount Applied",
]

TEXT_COLUMNS = [
    "Transaction ID",
    "Customer ID",
    "Category",
    "Item",
    "Payment Method",
    "Location",
]

NUMERIC_COLUMNS = [
    "Price Per Unit",
    "Quantity",
    "Total Spent",
]

BOOLEAN_VALUES = {
    "true",
    "false",
    "1",
    "0",
    "yes",
    "no",
}


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def is_missing(value):
    return value is None or value.strip().lower() in {
        "",
        "nan",
        "nat",
        "none",
        "null",
    }


def is_numeric(value):
    if is_missing(value):
        return True

    try:
        float(value)
        return True
    except ValueError:
        return False


def parse_date(value):
    if is_missing(value):
        return None

    value = value.strip()

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


def canonical_hash(rows, columns):
    normalized = []

    for row in rows:
        normalized.append(
            tuple((row.get(col) or "").strip() for col in columns)
        )

    normalized.sort()

    payload = "\n".join(
        "|".join(row)
        for row in normalized
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check_schema(columns):
    missing = sorted(set(EXPECTED_COLUMNS) - set(columns))
    extra = sorted(set(columns) - set(EXPECTED_COLUMNS))

    return missing, extra


def check_duplicate_rows(rows, columns):
    values = [
        tuple(row.get(col, "") for col in columns)
        for row in rows
    ]

    counts = Counter(values)

    return sum(count - 1 for count in counts.values() if count > 1)


def check_missing_ids(rows):
    bad = []

    for index, row in enumerate(rows, start=2):
        if (
            is_missing(row.get("Transaction ID"))
            or is_missing(row.get("Customer ID"))
        ):
            bad.append(index)

    return bad


def check_whitespace(rows):
    problems = []

    for index, row in enumerate(rows, start=2):
        for column in TEXT_COLUMNS:
            value = row.get(column)

            if value is not None and value != value.strip():
                problems.append((index, column, value))

    return problems


def check_numeric_columns(rows):
    problems = []

    for index, row in enumerate(rows, start=2):
        for column in NUMERIC_COLUMNS:
            value = row.get(column)

            if not is_numeric(value):
                problems.append((index, column, value))

    return problems


def check_dates(rows):
    problems = []

    for index, row in enumerate(rows, start=2):
        value = row.get("Transaction Date")

        if not is_missing(value) and parse_date(value) is None:
            problems.append((index, value))

    return problems

def check_date_semantics(reference_rows, output_rows):
    """
    Compare output Transaction Date values against a trusted reference
    dataset using Transaction ID as the key.
    """
    output_by_id = {
        row.get("Transaction ID", "").strip(): row
        for row in output_rows
        if not is_missing(row.get("Transaction ID"))
    }

    changed = []

    for row in reference_rows:
        transaction_id = row.get("Transaction ID", "").strip()

        if not transaction_id or transaction_id not in output_by_id:
            continue

        reference_raw = row.get("Transaction Date", "").strip()
        output_raw = output_by_id[transaction_id].get(
            "Transaction Date", ""
        ).strip()

        if is_missing(reference_raw):
            continue

        reference_date = parse_date(reference_raw)
        output_date = parse_date(output_raw)

        if (
            reference_date is None
            or output_date is None
            or reference_date.date() != output_date.date()
        ):
            changed.append(
                (transaction_id, reference_raw, output_raw)
            )

    return changed

def check_monetary_semantics(reference_rows, output_rows):
    """
    Compare monetary values against a trusted reference dataset using
    Transaction ID as the key.

    Detect systematic scale changes such as values becoming 100x larger.
    """
    output_by_id = {
        row.get("Transaction ID", "").strip(): row
        for row in output_rows
        if not is_missing(row.get("Transaction ID"))
    }

    ratios = []

    for row in reference_rows:
        transaction_id = row.get("Transaction ID", "").strip()

        if not transaction_id or transaction_id not in output_by_id:
            continue

        output_row = output_by_id[transaction_id]

        for column in ("Price Per Unit", "Total Spent"):
            reference_raw = row.get(column, "").strip()
            output_raw = output_row.get(column, "").strip()

            if is_missing(reference_raw) or is_missing(output_raw):
                continue

            try:
                reference_value = float(reference_raw)
                output_value = float(output_raw)
            except ValueError:
                continue

            if reference_value == 0:
                continue

            ratio = output_value / reference_value

            if ratio != 1.0:
                ratios.append(
                    (
                        transaction_id,
                        column,
                        reference_value,
                        output_value,
                        ratio,
                    )
                )

    return ratios

def check_boolean_values(rows):
    problems = []

    for index, row in enumerate(rows, start=2):
        value = row.get("Discount Applied")

        if is_missing(value):
            continue

        if value.strip().lower() not in BOOLEAN_VALUES:
            problems.append((index, value))

    return problems


def report(name, passed, details=""):
    status = "PASS" if passed else "FAIL"

    print(f"[{status}] {name}")

    if details:
        print(f"       {details}")

    return passed


def main():
    parser = argparse.ArgumentParser(
        description="Validate Rhombus retail pipeline output."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="CSV uploaded to S3.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="CSV exported by Rhombus to GCS.",
    )

    parser.add_argument(
        "--reference",
        help=(
            "Optional trusted baseline CSV used for semantic "
            "validation."
        ),
    )
    parser.add_argument(
        "--compare-output",
        help=(
            "Optional second output from the same input "
            "for determinism validation."
        ),
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    input_columns, input_rows = read_csv(input_path)
    output_columns, output_rows = read_csv(output_path)

    reference_rows = None

    if args.reference:
        reference_path = Path(args.reference)
        _, reference_rows = read_csv(reference_path)

    print("=" * 65)
    print("RHOMBUS PIPELINE DATA VALIDATION")
    print("=" * 65)

    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")

    print()
    print("--- Basic statistics ---")
    print(f"Input rows:  {len(input_rows)}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Input columns:  {len(input_columns)}")
    print(f"Output columns: {len(output_columns)}")

    print()
    print("--- Validation checks ---")

    results = []

    missing, extra = check_schema(output_columns)

    results.append(
        report(
            "Expected 11-column output schema",
            not missing and not extra and output_columns == EXPECTED_COLUMNS,
            f"missing={missing}, extra={extra}",
        )
    )

    duplicate_count = check_duplicate_rows(
        output_rows,
        output_columns,
    )

    results.append(
        report(
            "No exact duplicate output rows",
            duplicate_count == 0,
            f"duplicates={duplicate_count}",
        )
    )

    missing_ids = check_missing_ids(output_rows)

    results.append(
        report(
            "No rows with missing Transaction ID or Customer ID",
            len(missing_ids) == 0,
            f"violations={len(missing_ids)}",
        )
    )

    whitespace = check_whitespace(output_rows)

    results.append(
        report(
            "Text values have no leading/trailing whitespace",
            len(whitespace) == 0,
            f"violations={len(whitespace)}",
        )
    )

    numeric = check_numeric_columns(output_rows)

    results.append(
        report(
            "Numeric columns contain only numeric or missing values",
            len(numeric) == 0,
            f"violations={len(numeric)}",
        )
    )

    dates = check_dates(output_rows)

    results.append(
        report(
            "Transaction Date uses a valid ISO-style output format",
            len(dates) == 0,
            f"violations={len(dates)}",
        )
    )
    if reference_rows is not None:
        date_changes = check_date_semantics(
            reference_rows,
            output_rows,
        )

        results.append(
            report(
                "Transaction Date preserves reference date semantics",
                len(date_changes) == 0,
                f"semantic_changes={len(date_changes)}",
            )
        )

        if date_changes:
            print("       Example semantic changes:")
            for transaction_id, reference, transformed in date_changes[:5]:
                print(
                    f"       {transaction_id}: "
                    f"{reference} -> {transformed}"
                )
    if reference_rows is not None:
        monetary_changes = check_monetary_semantics(
            reference_rows,
            output_rows,
        )

        results.append(
            report(
                "Monetary values preserve reference scale",
                len(monetary_changes) == 0,
                f"scale_changes={len(monetary_changes)}",
            )
        )

        if monetary_changes:
            print("       Example monetary scale changes:")
            for (
                transaction_id,
                column,
                reference,
                transformed,
                ratio,
            ) in monetary_changes[:5]:
                print(
                    f"       {transaction_id} | {column}: "
                    f"{reference} -> {transformed} "
                    f"(ratio={ratio:.2f}x)"
                )

    booleans = check_boolean_values(output_rows)

    results.append(
        report(
            "Discount Applied contains recognized boolean values",
            len(booleans) == 0,
            f"violations={len(booleans)}",
        )
    )

    results.append(
        report(
            "Output row count does not exceed input row count",
            len(output_rows) <= len(input_rows),
            (
                f"input={len(input_rows)}, "
                f"output={len(output_rows)}"
            ),
        )
    )

    if args.compare_output:
        second_columns, second_rows = read_csv(
            Path(args.compare_output)
        )

        first_hash = canonical_hash(
            output_rows,
            output_columns,
        )

        second_hash = canonical_hash(
            second_rows,
            second_columns,
        )

        results.append(
            report(
                "Deterministic output across repeated runs",
                (
                    output_columns == second_columns
                    and first_hash == second_hash
                ),
                (
                    f"first={first_hash[:16]}..., "
                    f"second={second_hash[:16]}..."
                ),
            )
        )

    print()
    print("--- Summary ---")

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if all(results):
        print("Overall result: PASS")
        sys.exit(0)

    print("Overall result: FAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()
