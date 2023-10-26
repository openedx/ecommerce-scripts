import os
import shutil
import unittest
import tempfile

from unittest.mock import patch, MagicMock, mock_open
from testfixtures import TempDirectory

os.environ['LICENSE_KEY'] = '1234556'
from ..geoip import match_sha256, write, download_file  # noqa: E402


class GeoipTestCases(unittest.TestCase):

    @patch('urllib.request.urlopen')
    def test_sha256_mismatch(self, mock_urlopen='http://foo'):
        mock_sha256 = MagicMock()
        mock_sha256.getcode.return_value = 200
        mock_sha256.read.return_value = b'29cd163ffacb8fef0441ab3b7c246b64db4a7148362ed35ef59a5d64f' \
                                        b'bbd7f5c'
        mock_urlopen.return_value = mock_sha256

        temp_dir = TempDirectory()
        temp_dir.write('file.txt', b'testing sha256')

        file_path = os.path.join(temp_dir.path, 'file.txt')
        value = match_sha256(file_path, mock_urlopen)

        self.assertEqual(False, value)

        temp_dir.cleanup()

    @patch('urllib.request.urlopen')
    def test_sha256_match(self, mock_urlopen='http://foo'):
        mock_sha256 = MagicMock()
        mock_sha256.getcode.return_value = 200
        mock_sha256.read.return_value = b'78553549e63a1ad55ff0af86d3c23c7e5e8b6146d09fab87009ec769a3f' \
                                        b'f8fce'
        mock_sha256.__enter__.return_value = mock_sha256
        mock_urlopen.return_value = mock_sha256

        temp_dir = TempDirectory()
        temp_dir.write('file.txt', b'testing sha256')

        file_path = os.path.join(temp_dir.path, 'file.txt')
        value = match_sha256(file_path, mock_urlopen)

        self.assertEqual(True, value)

        temp_dir.cleanup()

    def test_file_not_found_raise(self):
        out_file = tempfile.NamedTemporaryFile(delete=False)
        existing_file_as_string = 'invalid/path/file'
        self.assertRaises(FileNotFoundError, write, out_file, existing_file_as_string)

    def test_file_content(self):
        existing_file = tempfile.NamedTemporaryFile(delete=False)
        existing_file.close()
        out_file = tempfile.NamedTemporaryFile(delete=False)
        with out_file as f:
            f.write(b'testing')
            out_file.seek(0)
            write(f, existing_file.name)

        f.close()

        with open(existing_file.name) as ex:
            with open(out_file.name) as f:
                self.assertEqual(f.read(), ex.read())

    @patch('urllib.request.urlretrieve')
    @patch('urllib.request.urlopen')
    def test_raise_value_error(self, mock_urlretrieve, mock_urlopen):
        mock_urlretrieve.return_value = MagicMock()

        mock_sha256 = MagicMock()
        mock_sha256.getcode.return_value = 200
        mock_sha256.read.return_value = b'cf80cd8aed482d5d1527d7dc72fceff84e6326592848447d2dc0b0e8' \
                                        b'7dfc9a90'
        mock_urlopen.return_value = mock_sha256

        mock_open = unittest.mock.mock_open(read_data=b'testing')

        with patch('builtins.open', mock_open, create=True):
            self.assertRaises(ValueError, download_file, 'path')
