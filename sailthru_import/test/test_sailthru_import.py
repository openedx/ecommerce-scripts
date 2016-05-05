from sailthru_import import sailthru_import
from sailthru.sailthru_client import SailthruClient

import unittest
import mock
from mock import patch


@patch('sailthru.sailthru_client')
class SailThruTestCase(unittest.TestCase):
    def test_upload_csv_to_sailthru(self, mock_client):
        mock_client.return_value.api_get.response.body.status.return_value = "completed"
        mock_client.upload_csv_to_sailthru('test.csv', 'list name', 'bfohl@edx.org', mock_client)
        mock_client.upload_csv_to_sailthru.assert_called_once()
