import argparse
import logging
import time
from sailthru.sailthru_client import SailthruClient

"""
Uploads a list of historical purchase files to Sailthru using job api.

Arguments:
    `file_name`: file name(s) to import.
    `report_email`: Email address which will receive report on import completion.
    `sailthru_key`: API key
    `sailthru_secret`: API secret

Example usage:
    $ import_job input1.txt,input2.txt "user@edx.org" AJKHSDKJHSADKJSH-1 KSJLAFUHDSUIH-2

Upload file size limit is 100 MB.

"""

logger = logging.getLogger(__name__)


def setup_logging():
    """ Setup logging.
    """
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')


def upload_to_sailthru(filepath, report_email, client):
    logger.info("Uploading %s" % filepath)
    # Start the upload job
    request_data = {
            'job': 'purchase_import',
            'file': filepath,
            'report_email': report_email
        }
    response = client.api_post('job', request_data, {'file': 1})

    if response.is_ok():
        job_id = response.get_body().get("job_id")
        logger.info("Import job started on SailThru - JOB ID: " + job_id)

        # Keeping checking status until we find out that it's done
        while True:
            time.sleep(10)
            response = client.api_get('job', {'job_id': job_id})
            if response.get_body().get("status") == "completed":
                return
    else:
        error = response.get_error()
        logger.error("Error: " + error.get_message())
        logger.error("Status Code: " + str(response.get_status_code()))
        logger.error("Error Code: " + str(error.get_error_code()))
        exit(1)


def main():
    parser = argparse.ArgumentParser(description='Sailthru order import script')
    parser.add_argument('file_names', help='Comma separated file name list for import.')
    parser.add_argument('report_email', help='Email address which will receive report on import completion.')
    parser.add_argument('sailthru_key', help='Sailthru access key.')
    parser.add_argument('sailthru_secret', help='Sailthru access secret.')
    args = parser.parse_args()

    sailthru_client = SailthruClient(args.sailthru_key, args.sailthru_secret)

    if args.file_names.find(',') != -1:
        # handle a comma separated list of json files
        file_list = args.file_names.split(',')
        for file_name in file_list:
            upload_to_sailthru(file_name, args.report_email, sailthru_client)
    else:
        # handle a single input CSV
        upload_to_sailthru(args.file_names, args.report_email, sailthru_client)

    logger.info("Import Complete!")

if __name__ == "__main__":
    setup_logging()
    main()
