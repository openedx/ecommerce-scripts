import sailthru_import
from sailthru_import import sailthru_import

import mock
import unittest

class SailThruTestCase(unittest.TestCase):
    def test_upload_csv_to_sailthru(self):
        mock_client = mock()
        sailthru_import.upload_csv_to_sailthru()