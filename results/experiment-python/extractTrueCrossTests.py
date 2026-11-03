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

    #
    # Full filtered CSV output
    #
    output_csv = os.path.join(
        directory,
        "ttc_" + basename
    )

    #
    # TXT output containing the values from column D
    #
    root_name, _ = os.path.splitext(basename)

    output_txt = os.path.join(
        directory,
        "ttc_" + root_name + ".txt"
    )

    total_rows = 0
    selected_rows = 0

    column_d_values = []

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
            print("Error: empty CSV file")
            sys.exit(3)

        #
        # Preserve original header
        #
        writer.writerow(header)

        for row in reader:

            total_rows += 1

            #
            # Required columns:
            # B -> index 1
            # D -> index 3
            # K -> index 10
            #
            if len(row) <= 10:
                continue

            column_b = row[1]
            column_k = row[10]

            if (
                is_dependent(column_b)
                and
                is_positive_numeric(column_k)
            ):

                writer.writerow(row)
                selected_rows += 1

                #
                # Save column D value
                #
                if len(row) > 3:
                    column_d_values.append(row[3])

    #
    # Generate TXT file
    #
    with open(
        output_txt,
        "w",
        encoding="utf-8"
    ) as txt_out:

        for value in column_d_values:
            txt_out.write(f"test_id= {value}\n")

    print()
    print("Processing completed successfully")
    print("-" * 60)
    print(f"Input file      : {input_file}")
    print(f"Output CSV file : {output_csv}")
    print(f"Output TXT file : {output_txt}")
    print(f"Rows processed  : {total_rows}")
    print(f"Rows selected   : {selected_rows}")
    print("-" * 60)
    print()


if __name__ == "__main__":
    main()
