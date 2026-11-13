#!/usr/bin/env python3

import argparse
import csv
import os
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Search for CSV files by prefix and generate a statistics file."
    )
    parser.add_argument("-p", "--prefix", required=True, help="File name prefix")
    parser.add_argument("directory", help="Directory to search in")
    parser.add_argument(
        "-o", "--outdir",
        default=".",
        help="Output directory for the statistics CSV (default: current directory)"
    )
    return parser.parse_args()


def find_files(directory: Path, prefix: str, ext: str) -> list[Path]:
    """Recursively search for files matching the given prefix and extension."""
    pattern = f"{prefix}*.{ext}"
    return sorted(directory.rglob(pattern))


def count_dependent_by_ef(filepath: Path) -> dict[tuple[str, str], int]:
    """Count occurrences of 'dependent' in column B (case-insensitive, stripped),
    grouped by unique (E, F) pairs (columns at index 4 and 5)."""
    counts: dict[tuple[str, str], int] = {}
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if len(row) >= 2 and row[1].strip().lower() == "dependent":
                    col_e = row[4].strip() if len(row) > 4 else ""
                    col_f = row[5].strip() if len(row) > 5 else ""
                    key = (col_e, col_f)
                    counts[key] = counts.get(key, 0) + 1
    except Exception as e:
        print(f"Warning: unable to read '{filepath}': {e}", file=sys.stderr)
    return counts


def get_warning(source: str, target: str) -> str:
    """Return a warning message based on source and target values."""
    if not source and not target:
        return "Empty fields: source and target not found. Possibly there are no True cross-tests from the source that are applicable on the target"
    if not source:
        return "Empty source"
    if not target:
        return "Empty target"
    if source.lower() == target.lower():
        return "Same implementation"
    return ""


def build_csv(files: list[Path], output_path: Path):
    """Write the output CSV with one row per unique (filename, E, F) combination and its count."""
    fieldnames = ["Input File", "Source Implementation", "Target Implementation", "Warnings", "Number of True Cross Tests"]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for f in files:
            counts = count_dependent_by_ef(f)
            if counts:
                for (col_e, col_f), count in sorted(counts.items()):
                    warning = get_warning(col_e, col_f)
                    writer.writerow({
                        "Input File": f.name,
                        "Source Implementation": col_e,
                        "Target Implementation": col_f,
                        "Warnings": warning,
                        "Number of True Cross Tests": count,
                    })
            else:
                # file found but no matching rows
                writer.writerow({
                    "Input File": f.name,
                    "Source Implementation": "",
                    "Target Implementation": "",
                    "Warnings": "Empty fields: source and target not found. Possibly there are no True cross-tests from the source that are applicable on the target",
                    "Number of True Cross Tests": 0,
                })


def main():
    args = parse_args()

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    outdir = Path(args.outdir)
    if not outdir.is_dir():
        print(f"Error: output directory '{outdir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Searching for files with prefix='{args.prefix}' and extension='.csv' in '{directory}' ...")
    files = find_files(directory, args.prefix, "csv")

    if not files:
        print("No files found.")
    else:
        print(f"Found {len(files)} file(s).")

    output_path = outdir / f"statistics_{args.prefix}.csv"
    build_csv(files, output_path)
    print(f"Output saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
