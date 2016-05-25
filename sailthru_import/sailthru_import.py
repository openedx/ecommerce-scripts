import argparse
import logging
import os
import time
from sailthru.sailthru_client import SailthruClient

"""
Uploads a specified CSV file containing users into SailThru via the Job API endpoint.

Arguments:
    `sailthru_key`: API key
    `sailthru_secret`: API secret
    `csv_file_name`: CSV file name to import.
    `list_name`: List name to import users into.
    `report_email`: Email address which will receive report on import completion.

Example usage:
    $ sailthru_import AJKHSDKJHSADKJSH-1 KSJLAFUHDSUIH-2 input.csv "Dev Test" "bfohl@edx.org"

Upload file size limit is 100 MB. csv_splitter is used to break up the export file from MailChimp.

csvcut (part of csvkit) is recommended for filtering out the necessary fields:
    csvcut -c "Email Address","activated","Age","Country","date_joined",
    "DSTOFF","EUID","Gender","GMTOFF","id","last_login","LEID","MEMBER_RATING",
    "REGION","TIMEZONE","Username","year_of_birth"
    ~/Downloads/members_export_107aacb22a.csv -e ISO-8859-1 > Downloads/members_export_filtered_2.csv

"""


def upload_csv_to_sailthru(filepath, list_name, report_email, client):
    logging.info("Uploading %s" % filepath)
    # Start the upload job
    request_data = {
            'job': 'import',
            'file': filepath,
            'list': list_name,
            'signup_dates': 1,
            'report_email': report_email
        }
    response = client.api_post('job', request_data, {'file': 1})

    if response.is_ok():
        job_id = response.get_body().get("job_id")
        logging.info("Import job started on SailThru - JOB ID: " + job_id)

        # Keeping checking status until we find out that it's done
        while True:
            logging.info("waiting for import to complete...")
            time.sleep(30)
            response = client.api_get('job', {'job_id': job_id})
            if response.get_body().get("status") == "completed":
                return
    else:
        error = response.get_error()
        logging.error("Error: " + error.get_message())
        logging.error("Status Code: " + str(response.get_status_code()))
        logging.error("Error Code: " + str(error.get_error_code()))
        exit(1)


def main():
    parser = argparse.ArgumentParser(description='Sailthru user import script')
    parser.add_argument('csv_file_name', help='CSV file name for import.')
    parser.add_argument('list_name', help='SailThru list name to import users into.')
    parser.add_argument('report_email', help='Email address which will receive report on import completion.')
    parser.add_argument('sailthru_key', help='Sailthru access key.')
    parser.add_argument('sailthru_secret', help='Sailthru access secret.')
    args = parser.parse_args()

    sailthru_client = SailthruClient(args.sailthru_key, args.sailthru_secret)

    if args.csv_file_name.find(',') != -1:
        # handle a comma separated list of CSV files
        file_list = args.csv_file_name.split(',')
        for file_name in file_list:
            upload_csv_to_sailthru(file_name, args.list_name, args.report_email, sailthru_client)
    else:
        # handle a single input CSV
        upload_csv_to_sailthru(args.csv_file_name, args.list_name, args.report_email, sailthru_client)

    logging.info("Import Complete!")

if __name__ == "__main__":
    main()
