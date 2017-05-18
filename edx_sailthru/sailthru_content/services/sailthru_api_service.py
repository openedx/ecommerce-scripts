import json
import logging
import os
import tempfile
import time

from sailthru.sailthru_client import SailthruClient


class SailthruApiService(object):
    """The service to interface with Sailthru API"""
    def __init__(self, sailthru_key, sailthru_secret, content_url_root):
        self.sailthru_client = SailthruClient(sailthru_key, sailthru_secret)
        self.content_url_root = content_url_root

    def list(self, list_size=1000):
        sailthru_content_list = []
        response = self.sailthru_client.api_get('content', {'items': list_size})

        if not response.is_ok():
            logging.error(
                "Error code %d connecting to Sailthru content api: %s",
                response.json['error'],
                response.json['errormsg']
            )
        else:
            for body in response.json['content']:
                logging.info(body)
                sailthru_content_list.append(body)

        return sailthru_content_list

    def _upload_batch_file(self, filepath, report_email=None):
        """Use Sailthru job API to upload all content as a batch job"""
        logging.info("Uploading %s" % filepath)
        request_data = {
            'job': 'content_update',
            'file': filepath,
            'report_email': report_email
        }
        response = self.sailthru_client.api_post('job', request_data, {'file': 1})

        if response.is_ok():
            job_id = response.get_body().get("job_id")
            logging.info("Import job started on SailThru - JOB ID: " + job_id)

            # Keeping checking status until we find out that it's done
            while True:
                logging.info("waiting for import to complete...")
                time.sleep(10)
                response = self.sailthru_client.api_get('job', {'job_id': job_id})
                if response.get_body().get("status") == "completed":
                    return

        else:
            error = response.get_error()
            logging.error("Error: " + error.get_message())
            logging.error("Status Code: " + str(response.get_status_code()))
            logging.error("Error Code: " + str(error.get_error_code()))

    def upload(self, library_items, report_email=None):
        if not library_items:
            return

        with tempfile.NamedTemporaryFile(delete=False, mode='w+t') as tmp_file:
            for item in library_items:
                json.dump(item, tmp_file)
                tmp_file.write('\n')
            tmp_file.close()
            self._upload_batch_file(tmp_file.name, report_email)
            os.unlink(tmp_file.name)

    def clear(self):
        while True:
            response = self.sailthru_client.api_get('content', {'items': 4000})

            if not response.is_ok():
                logging.error(
                    "Error code %d connecting to Sailthru content api: %s",
                    response.json['error'],
                    response.json['errormsg']
                )
                return

            sailthru_content = response.json['content']
            if not sailthru_content:
                logging.info('Content cleared')
                return

            for body in sailthru_content:
                item_key = body.get('url')
                if item_key:
                    response = self.sailthru_client.api_delete('content', {'url': item_key})
                    if response.is_ok():
                        logging.info("content item %s deleted", item_key)
                    else:
                        logging.info("content item %s delete encountered errors", item_key)
