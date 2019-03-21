import shutil
import unittest
import tempfile


from unittest.mock import patch, MagicMock, mock_open

from ..geoip import match_md5, write, download_file


class GeoipTestCases(unittest.TestCase):

    @patch('urllib.request.urlopen')
    def test_md5_mismatch(self, mock_urlopen='http://foo'):
        mock_md5 = MagicMock()
        mock_md5.getcode.return_value = 200
        mock_md5.read.return_value = '4059D862F09C315470DC8FF0FF6EBCAF'.encode('utf-8')
        mock_urlopen.return_value = mock_md5

        temp_file = tempfile.NamedTemporaryFile(delete=False)
        with temp_file as f:
            f.write('testing md5'.encode('utf-8'))
            f.seek(0)
            value = match_md5(f, mock_urlopen)

        self.assertEqual(False, value)

    @patch('urllib.request.urlopen')
    def test_md5_match(self, mock_urlopen='http://foo'):
        mg = MagicMock()
        mg.getcode.return_value = 200
        mg.read.return_value = '4059d862f09c315470dc8ff0ff6ebcaf'.encode('utf-8')
        mg.__enter__.return_value = mg
        mock_urlopen.return_value = mg

        temp_file = tempfile.NamedTemporaryFile(delete=False)
        with temp_file as f:
            f.write('testing md5'.encode('utf-8'))
            f.seek(0)
            value = match_md5(f, mock_urlopen)

        self.assertEqual(True, value)

    def test_shutil_raise(self):
        out_file = tempfile.NamedTemporaryFile(delete=False)
        existing_file_as_string = 'random'
        self.assertRaises(shutil.Error, write(out_file, existing_file_as_string))

    def test_file_content(self):
        existing_file = tempfile.NamedTemporaryFile(delete=False)
        existing_file.close()
        out_file = tempfile.NamedTemporaryFile(delete=False)
        with out_file as f:
            f.write('testing'.encode('utf-8'))
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

        mock_md5 = MagicMock()
        mock_md5.getcode.return_value = 200
        mock_md5.read.return_value = '4059d862f09c315470dc8ff0ff6ebcaw'.encode('utf-8')
        mock_urlopen.return_value = mock_md5

        mock_open = unittest.mock.mock_open(read_data='testing'.encode('utf-8'))

        with patch('gzip.open', mock_open, create=True):
            self.assertRaises(ValueError, download_file, 'path')



