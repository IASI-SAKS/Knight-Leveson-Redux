#!/usr/bin/env python3

import json
import sys
from collections import defaultdict


def load_jsonl(filename):
    records = []

    with open(filename, "r", encoding="utf-8") as fp:

        for lineno, line in enumerate(fp, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Errore JSON alla riga {lineno}: {exc}"
                )

    return records


def generate_report(records):

    groups = defaultdict(list)

    for record in records:

        version_id = record["version_id"]

        coverage = record.get("coverage", {})

        groups[version_id].append(
            {
                "test_id": record["test_id"],
                "line_percent": coverage.get(
                    "line_percent", 0.0
                ),
                "covered_lines": coverage.get(
                    "covered_lines", 0
                ),
                "total_lines": coverage.get(
                    "total_lines", 0
                ),
                "branch_percent": coverage.get(
                    "branch_percent", 0.0
                ),
                "covered_branches": coverage.get(
                    "covered_branches", 0
                ),
                "total_branches": coverage.get(
                    "total_branches", 0
                ),
            }
        )

    output = []

    for version_id in sorted(groups):

        output.append(version_id)
        output.append("-" * 48)

        tests = sorted(
            groups[version_id],
            key=lambda x: x["test_id"]
        )

        for test in tests:

            output.append(
                f"test_id= {test['test_id']:2d} | "
                f"lines= {test['line_percent']:.2f}% "
                f"({test['covered_lines']}/{test['total_lines']}) | "
                f"branches= {test['branch_percent']:.2f}% "
                f"({test['covered_branches']}/{test['total_branches']})"
            )

    return "\n".join(output)


def main():

    if len(sys.argv) != 3:

        print(
            "Usage:\n"
            "  python jsonl_to_txt.py inputJSONL.txt out.txt"
        )

        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    records = load_jsonl(input_file)

    report = generate_report(records)

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as fp:
        fp.write(report)

    print(
        f"Creato '{output_file}' con "
        f"{len(records)} record."
    )


if __name__ == "__main__":
    main()
