import argparse
import csv
import logging
import os

"""
Splits a CSV file into multiple pieces.

Arguments:

    `row_limit`: The number of rows you want in each output file. 10,000 by default.
    `output_name_template`: A %s-style template for the numbered output files.
    `output_path`: Where to stick the output files.
    `keep_headers`: Whether or not to print the headers in each output file.

Example usage:
    >> csv_splitter.split(open('/home/ben/input.csv', 'r'));

"""


def split(filehandler, delimiter=',', row_limit=500000,
          output_name_template='output_%s.csv', output_path='.', keep_headers=True):

    logging.info("Beginning split...")
    reader = csv.reader(filehandler, delimiter=delimiter)
    current_piece = 1
    current_out_path = os.path.join(
         output_path,
         output_name_template % current_piece
    )
    current_out_writer = csv.writer(open(current_out_path, 'w'), delimiter=delimiter)
    current_limit = row_limit
    if keep_headers:
        headers = reader.next()
        # rename "Email Address" header to "email", this is required to be in the first column, and rename
        # date fields to end
        headers[0] = 'email'
        headers[4] = 'joined_date'
        headers[10] = 'last_login_date'
        # make headers lowercase
        headers = [header.lower() for header in headers]
        current_out_writer.writerow(headers)
    for i, row in enumerate(reader):
        if i + 1 > current_limit:
            current_piece += 1
            current_limit = row_limit * current_piece
            current_out_path = os.path.join(
               output_path,
               output_name_template % current_piece
            )
            current_out_writer = csv.writer(open(current_out_path, 'w'), delimiter=delimiter)
            if keep_headers:
                current_out_writer.writerow(headers)
        current_out_writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description='CSV splitter script')
    parser.add_argument('input_file', help='Input file name.')
    args = parser.parse_args()
    logging.info("Input file: " + args.input_file)

    split(open(args.input_file, 'r'))


if __name__ == "__main__":
    main()
