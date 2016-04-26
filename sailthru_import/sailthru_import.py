import argparse
import time
from sailthru.sailthru_client import SailthruClient
from sailthru.sailthru_error import SailthruClientError

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

"""


def upload_csv_to_sailthru(filepath, list_name, report_email, client):
    try:
        print "Uploading %s" % filepath
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
            print "Import job started on SailThru - JOB ID: " + job_id

            # Keeping checking status until we find out that it's done
            while True:
                print("waiting for import to complete...")
                time.sleep(30)
                response = client.api_get('job', {'job_id': job_id})
                if response.get_body().get("status") == "completed":
                    return
        else:
            error = response.get_error()
            print ("Error: " + error.get_message())
            print ("Status Code: " + str(response.get_status_code()))
            print ("Error Code: " + str(error.get_error_code()))
    except SailthruClientError as e:
        print ("Exception")
        print (e)


def main():
    parser = argparse.ArgumentParser(description='Sailthru user import script')
    parser.add_argument('sailthru_key', help='Sailthru access key.')
    parser.add_argument('sailthru_secret', help='Sailthru access secret.')
    parser.add_argument('csv_file_name', help='CSV file name for import.')
    parser.add_argument('list_name', help='SailThru list name to import users into.')
    parser.add_argument('report_email', help='Email address which will receive report on import completion.')
    args = parser.parse_args()

    sailthru_client = SailthruClient(args.sailthru_key, args.sailthru_secret)
    upload_csv_to_sailthru(args.csv_file_name, args.list_name, args.report_email, sailthru_client)
    print "Import Complete!"

if __name__ == "__main__":
    main()
