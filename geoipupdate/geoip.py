import hashlib
import os
import urllib
import tarfile
import shutil
import logging


license_key = os.environ['LICENSE_KEY']
MAXMIND_URL = 'https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country' \
              '&license_key={key}&suffix=tar.gz'.format(key=license_key)
MAXMIND_SHA256_URL = 'https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country' \
                     '&license_key={key}&suffix=tar.gz.sha256'.format(key=license_key)
LOCAL_FILENAME = 'GeoLite2-Country.mmdb'
GEOIP_PATH = "/common/static/data/geoip/"


def match_sha256(_file, sha256_url):
    """

    Purpose of the method to make sure downloaded file is accurate.

    Args:
         _file (file): downloaded file
         sha256_url (str): url to read sha256 hash of file

    Returns:
        bool: Returns True if downloaded file hash and hash returned by url
        are same otherwise returns False

    """
    sha256 = urllib.request.urlopen(sha256_url).read()
    hash_object = hashlib.sha256()
    file_content = open(_file, 'rb').read()
    hash_object.update(file_content)

    return hash_object.hexdigest() in sha256.decode()


def write(outfile, existing_file):
    """

    Copy the newly downloaded file to existing file

    Args:
        outfile (File): downloaded file from url
        existing_file (File): existing file in directory

    Returns:
        None

    Raises:
        any exception that occurs during writing the file

    """
    try:
        logging.info("Writing downloaded file to existing file.")
        with open(existing_file, 'wb') as exfile:
            shutil.copyfileobj(outfile, exfile)
    except:
        raise


def download_file(current_directory):
    """

    Downloads the file and check sha256 hash to make sure file is downloaded correctly. If doesn't
    match then it would abort operation otherwise continue copying the file

    Args:
        current_directory: current process directory which would be edx-platform repo

    Returns:
        None

    Raises:
        ValueError: if sha256 hash of downloaded file doesn't match

    """
    logging.info("Downloading maxmind geoip2 country database.")
    existing_file = os.path.join(current_directory + GEOIP_PATH, LOCAL_FILENAME)
    downloaded_file, headers = urllib.request.urlretrieve(
        MAXMIND_URL
    )
    logging.info("Downloading completed geoip2 country database.")

    if match_sha256(downloaded_file, MAXMIND_SHA256_URL):

        with tarfile.open(downloaded_file, 'r:gz') as outfile:
            for member in outfile.getmembers():
                if LOCAL_FILENAME in member.name:
                    _file = outfile.extractfile(member)
                    write(_file, existing_file)
        os.remove(downloaded_file)
    else:
        logging.info("Downloaded file hash did't matched. Aborting the operation")
        try:
            os.remove(downloaded_file)
        finally:
            raise ValueError(
                'sha256 of %s doesn\'t match the signature.' % downloaded_file
            )
