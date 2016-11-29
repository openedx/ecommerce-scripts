import mock
import unittest

from faker import Factory

from services.sailthru_api_service import SailthruApiService


class SailthruApiServiceTests(unittest.TestCase):
    def setUp(self):
        self.faker = Factory.create()
        self.sailthru_key = self.faker.password()
        self.sailthru_secret = self.faker.password()
        self.content_url_root = 'http://' + self.faker.domain_name()
        self.sailthru_client = SailthruApiService(self.sailthru_key, self.sailthru_secret, self.content_url_root)
        self.mock_sailthru_list = {
            'content': [
                {
                    "url": "http://" + self.faker.domain_name()
                },
                {
                    "url": "http://" + self.faker.domain_name()
                },
            ]
        }

    def _get_api_get_response_mock(self, is_ok_value, side_effect):
        get_response_mock = mock.Mock()
        get_response_mock.is_ok.return_value = is_ok_value
        json_property = mock.PropertyMock(side_effect=side_effect)
        type(get_response_mock).json = json_property
        return get_response_mock

    @mock.patch('sailthru.sailthru_client.SailthruClient.api_get')
    def test_list_success(self, mock_api_get):
        get_response_mock = self._get_api_get_response_mock(True, [self.mock_sailthru_list])
        mock_api_get.return_value = get_response_mock
        sailthru_item_collection = self.sailthru_client.list()
        self.assertEqual(len(sailthru_item_collection), len(self.mock_sailthru_list['content']))

    @mock.patch('sailthru.sailthru_client.SailthruClient.api_get')
    @mock.patch('logging.error')
    def test_list_error(self, mock_error_log, mock_api_get):
        error_result = {
            'errormsg': 'mock error message',
            'error': 22
        }
        mock_get_result = mock.Mock(json=error_result)
        mock_get_result.is_ok.return_value = False
        mock_api_get.return_value = mock_get_result
        sailthru_item_collection = self.sailthru_client.list()
        self.assertEqual(len(sailthru_item_collection), 0)
        self.assertTrue(mock_error_log.called)

    @mock.patch('sailthru.sailthru_client.SailthruClient.api_get')
    @mock.patch('sailthru.sailthru_client.SailthruClient.api_delete')
    def test_clear_success(self, mock_api_delete, mock_api_get):
        get_response_mock = self._get_api_get_response_mock(True, [self.mock_sailthru_list, {'content': []}])
        mock_api_get.return_value = get_response_mock

        delete_response_mock = mock.Mock()
        delete_response_mock.is_ok.return_value = True
        mock_api_delete.return_value = delete_response_mock
        self.sailthru_client.clear()
        self.assertTrue(mock_api_get.called)
        self.assertTrue(mock_api_delete.called)
        self.assertTrue(get_response_mock.is_ok.called)
        self.assertTrue(delete_response_mock.is_ok.called)

    @mock.patch('sailthru.sailthru_client.SailthruClient.api_get')
    def test_clear_no_item(self, mock_api_get):
        get_response_mock = self._get_api_get_response_mock(True, [self.mock_sailthru_list, {'content': []}])
        mock_api_get.return_value = get_response_mock

        self.sailthru_client.clear()
        self.assertTrue(mock_api_get.called)
        self.assertTrue(get_response_mock.is_ok.called)

    @mock.patch('sailthru.sailthru_client.SailthruClient.api_get')
    @mock.patch('sailthru.sailthru_client.SailthruClient.api_delete')
    def test_clear_delete_error(self, mock_api_delete, mock_api_get):
        get_response_mock = self._get_api_get_response_mock(True, [self.mock_sailthru_list, {'content': []}])
        mock_api_get.return_value = get_response_mock

        delete_response_mock = mock.Mock()
        delete_response_mock.is_ok.return_value = False
        mock_api_delete.return_value = delete_response_mock
        self.sailthru_client.clear()
        self.assertTrue(mock_api_get.called)
        self.assertTrue(mock_api_delete.called)
        self.assertTrue(get_response_mock.is_ok.called)
        self.assertTrue(delete_response_mock.is_ok.called)

    @mock.patch('sailthru.sailthru_client.SailthruClient.api_get')
    @mock.patch('sailthru.sailthru_client.SailthruClient.api_post')
    @mock.patch('time.sleep')
    def test_upload_batch_file_success(self, mock_sleep, mock_api_post, mock_api_get):
        mock_job_id = str(self.faker.pyint())
        get_response_mock = mock.Mock()
        get_response_mock.get_body.side_effect = [
            {'status': 'InProgress'},
            {'status': 'completed'},
        ]
        mock_api_get.return_value = get_response_mock

        post_response_mock = mock.Mock()
        post_response_mock.is_ok.return_value = True
        post_response_mock.get_body.return_value = {'job_id': mock_job_id}
        mock_api_post.return_value = post_response_mock

        mock_sleep.return_value = True

        self.sailthru_client._upload_batch_file(self.faker.uri_path())
        self.assertTrue(mock_api_post.called)
        self.assertTrue(mock_api_get.called)

    @mock.patch('logging.error')
    @mock.patch('sailthru.sailthru_client.SailthruClient.api_post')
    def test_upload_batch_file_failure(self, mock_api_post, mock_error_log):
        error_mock = mock.Mock()
        error_mock.get_message.return_value = 'Test error'
        error_mock.get_status_code.return_value = 500
        error_mock.get_error_code.return_value = 'Test error code'
        post_response_mock = mock.Mock()
        post_response_mock.is_ok.return_value = False
        post_response_mock.get_error.return_value = error_mock
        mock_api_post.return_value = post_response_mock

        self.sailthru_client._upload_batch_file(self.faker.uri_path())
        self.assertTrue(mock_error_log.called)
