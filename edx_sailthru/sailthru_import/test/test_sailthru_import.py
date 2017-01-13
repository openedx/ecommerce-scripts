import unittest

from mock import patch

from edx_sailthru.sailthru_import import sailthru_import


@patch('time.sleep')
@patch('sailthru.sailthru_client')
class SailThruTestCase(unittest.TestCase):
    def test_upload_csv_to_sailthru(self, mock_client, mock_sleep):
        mock_client.api_get.return_value.get_body.return_value = {'status': 'completed'}
        mock_client.api_post.return_value.is_ok.return_value = True
        mock_sleep.return_value = True
        sailthru_import.upload_csv_to_sailthru('test.csv', 'list name', 'bfohl@edx.org', mock_client)
        mock_client.api_post.assert_called_once()
        mock_sleep.assert_called_once()
        mock_client.api_get.assert_called_once()
