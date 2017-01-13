import argparse
import csv
import logging
import os

"""
Split the Mailchimp csv file in to multiple pieces and change column names

File from Mailchimp should be reduced with the following commands before running:

pip install csvkit
csvcut -c "Email Address","activated","Age","Country","First Name","LAST_CHANGED","Name","date_joined","DSTOFF","EUID","Gender","GMTOFF","id","last_login","LEID","MEMBER_RATING","REGION","TIMEZONE","Username","year_of_birth" ~/Downloads/members_export_eccf291e61.csv -e ISO-8859-1 > ~/Downloads/members_export_filtered.csv

"""


def split(filehandler, delimiter=',', row_limit=1000000,
          output_name_template='output_%s.csv', output_path='.', keep_headers=True):

    # columns to rename
    renames = [['Email Address', 'email'],
               ['date_joined', 'joined_date'],
               ['LAST_CHANGED', 'last_changed_date'],
               ['Name', 'full name'],
               ['last_login', 'last_login_date']]

    logging.info("Splitter called")
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

        for rename in renames:
            if not rename_row(headers, rename[0], rename[1]):
                return

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
            # return
            current_out_writer = csv.writer(open(current_out_path, 'w'), delimiter=delimiter)

            if keep_headers:
                current_out_writer.writerow(headers)
        row[7] = '2016-07-21'
        current_out_writer.writerow(row)


def rename_row(headers, input_row, output):
    for i, value in enumerate(headers):
        if value == input_row:
            headers[i] = output
            return True

    logging.error("Unable to find column %s", input_row)
    return True


def main():
    parser = argparse.ArgumentParser(description='CSV splitter script')
    parser.add_argument('input_file', help='Input file name.')
    args = parser.parse_args()
    logging.info("Input file: " + args.input_file)

    split(open(args.input_file, 'r'))


if __name__ == "__main__":
    main()
