#!/usr/bin/env python3

import csv
import os
import sys


def is_dependent(value):
    """
    Returns True if column B contains 'dependent'
    (case-insensitive).
    """
    if value is None:
        return False

    return str(value).strip().lower() == "dependent"


def is_positive_numeric(value):
    """
    Returns True if:
      - value is not N/A
      - value is numeric
      - value is greater than zero
    """

    if value is None:
        return False

    value = str(value).strip()

    if value.upper() == "N/A":
        return False

    try:
        return float(value) > 0
    except ValueError:
        return False


def process_file(
    input_file,
    output_csv,
    output_txt,
    filter_column_index
):
    """
    Process the CSV using the specified filter column.

    filter_column_index:
        10 = column K (line coverage)
        15 = column P (branch coverage)
    """

    total_rows = 0
    selected_rows = 0

    selected_test_ids = []

    with open(
        input_file,
        "r",
        encoding="utf-8",
        newline=""
    ) as infile, open(
        output_csv,
        "w",
        encoding="utf-8",
        newline=""
    ) as csv_out:

        reader = csv.reader(infile)
        writer = csv.writer(csv_out)

        try:
            header = next(reader)
        except StopIteration:
            raise RuntimeError("Input CSV is empty")

        #
        # Preserve original header
        #
        writer.writerow(header)

        for row in reader:

            total_rows += 1

            #
            # Required columns:
            # B = index 1
            # D = index 3
            # K = index 10
            # P = index 15
            #
            if len(row) <= max(filter_column_index, 3):
                continue

            column_b = row[1]
            filter_value = row[filter_column_index]

            if (
                is_dependent(column_b)
                and
                is_positive_numeric(filter_value)
            ):

                writer.writerow(row)
                selected_rows += 1

                #
                # Save column D value (test_id)
                #
                selected_test_ids.append(row[3])

    #
    # Generate TXT file
    #
    with open(
        output_txt,
        "w",
        encoding="utf-8"
    ) as txt_out:

        for test_id in selected_test_ids:
            txt_out.write(f"test_id= {test_id}\n")

    return total_rows, selected_rows


def main():

    if len(sys.argv) != 2:

        print(
            f"Usage:\n"
            f"  python {os.path.basename(sys.argv[0])} input.csv"
        )

        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.isfile(input_file):

        print(f"Error: file not found: {input_file}")
        sys.exit(2)

    basename = os.path.basename(input_file)
    directory = os.path.dirname(input_file)

    root_name, _ = os.path.splitext(basename)

    #
    # LINE output files
    #
    line_csv = os.path.join(
        directory,
        f"tcts_line_{basename}"
    )

    line_txt = os.path.join(
        directory,
        f"tcts_line_{root_name}.txt"
    )

    #
    # BRANCH output files
    #
    branch_csv = os.path.join(
        directory,
        f"tcts_branch_{basename}"
    )

    branch_txt = os.path.join(
        directory,
        f"tcts_branch_{root_name}.txt"
    )

    #
    # Process LINE coverage
    # Filter on column K
    #
    total_rows, line_rows = process_file(
        input_file=input_file,
        output_csv=line_csv,
        output_txt=line_txt,
        filter_column_index=10
    )

    #
    # Process BRANCH coverage
    # Filter on column P
    #
    _, branch_rows = process_file(
        input_file=input_file,
        output_csv=branch_csv,
        output_txt=branch_txt,
        filter_column_index=15
    )

    print()
    print("Processing completed successfully")
    print("-" * 70)
    print(f"Input file           : {input_file}")
    print("-" * 70)

    print(f"Line CSV output      : {line_csv}")
    print(f"Line TXT output      : {line_txt}")
    print(f"Selected line rows   : {line_rows}")

    print("-" * 70)

    print(f"Branch CSV output    : {branch_csv}")
    print(f"Branch TXT output    : {branch_txt}")
    print(f"Selected branch rows : {branch_rows}")

    print("-" * 70)

    print(f"Total rows processed : {total_rows}")

    print("-" * 70)
    print()


if __name__ == "__main__":
    main()
