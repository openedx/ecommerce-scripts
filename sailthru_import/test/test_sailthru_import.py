from sailthru_import import sailthru_import
from sailthru.sailthru_client import SailthruClient

import unittest
import mock
from mock import patch


@patch('sailthru.sailthru_client')
class SailThruTestCase(unittest.TestCase):
    def test_upload_csv_to_sailthru(self, mock_client):
        mock_client.api_get.return_value.get_body.return_value = {'status': 'completed'}
        mock_client.api_post.return_value.is_ok.return_value = True
        sailthru_import.upload_csv_to_sailthru('test.csv', 'list name', 'bfohl@edx.org', mock_client)
        mock_client.upload_csv_to_sailthru.assert_called_once()
