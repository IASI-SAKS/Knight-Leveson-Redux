#!/usr/bin/env python3

import argparse
import csv
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute average Number of True Cross Tests per (Source, Target) pair across multiple CSV files."
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="List of input CSV files"
    )
    parser.add_argument(
        "-d", "--dir",
        help="Directory to search for input CSV files"
    )
    parser.add_argument(
        "-p", "--prefix",
        help="File name prefix filter (required when using -d|--dir)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file path (default: ./statistics_tcts_avg.csv)"
    )

    args = parser.parse_args()

    # Validate: either files or --dir must be provided, but not both
    if args.dir and args.files:
        parser.error("provide either a list of files or --dir, not both")
    if not args.dir and not args.files:
        parser.error("provide either a list of files or --dir")
    if args.dir and not args.prefix:
        parser.error("--prefix is required when using --dir")

    return args


def collect_files(args) -> list[Path]:
    """Collect input files either from positional args or by searching a directory."""
    if args.dir:
        directory = Path(args.dir)
        if not directory.is_dir():
            print(f"Error: '{directory}' is not a valid directory.", file=sys.stderr)
            sys.exit(1)
        files = sorted(directory.rglob(f"{args.prefix}*.csv"))
        if not files:
            print(f"No CSV files found with prefix '{args.prefix}' in '{directory}'.", file=sys.stderr)
            sys.exit(1)
        return files
    else:
        files = [Path(f) for f in args.files]
        missing = [f for f in files if not f.is_file()]
        if missing:
            for f in missing:
                print(f"Error: file not found: '{f}'", file=sys.stderr)
            sys.exit(1)
        return files


def read_csv(filepath: Path) -> list[dict]:
    """Read a statistics CSV and return its rows as a list of dicts."""
    rows = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"Warning: unable to read '{filepath}': {e}", file=sys.stderr)
    return rows


def compute_averages(files: list[Path]) -> list[dict]:
    """Compute average Number of True Cross Tests per (Source, Target) pair,
    collecting and deduplicating warnings across all input files."""
    # { (source, target): [values] }
    accumulator: dict[tuple[str, str], list[int]] = {}
    # { (source, target): [unique warnings] }
    warnings: dict[tuple[str, str], list[str]] = {}

    for filepath in files:
        rows = read_csv(filepath)
        for row in rows:
            source = row.get("Source Implementation", "").strip()
            target = row.get("Target Implementation", "").strip()
            try:
                value = int(row.get("Number of True Cross Tests", 0))
            except ValueError:
                value = 0
            warning = row.get("Warnings", "").strip()
            key = (source, target)
            accumulator.setdefault(key, []).append(value)

            # Deduplicate warnings case-insensitively
            if warning:
                existing = warnings.setdefault(key, [])
                if not any(w.strip().lower() == warning.lower() for w in existing):
                    existing.append(warning)

    results = []
    for (source, target), values in sorted(accumulator.items()):
        avg = sum(values) / len(values)
        combined_warnings = " | ".join(warnings.get((source, target), []))
        results.append({
            "Number of Files": len(values),
            "Source Implementation": source,
            "Target Implementation": target,
            "Warnings": combined_warnings,
            "Number of True Cross Tests": round(avg, 2),
        })

    return results


def write_output(results: list[dict], output_path: Path):
    """Write the averages to the output CSV file."""
    fieldnames = [
        "Number of Files",
        "Source Implementation",
        "Target Implementation",
        "Warnings",
        "Number of True Cross Tests",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    args = parse_args()

    files = collect_files(args)
    print(f"Processing {len(files)} file(s) ...")

    results = compute_averages(files)
    print(f"Found {len(results)} unique (Source, Target) pair(s).")

    output_path = Path(args.output) if args.output else Path("statistics_tcts_avg.csv")
    write_output(results, output_path)
    print(f"Output saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
