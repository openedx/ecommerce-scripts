import hashlib
import os
import urllib
import gzip
import shutil
import logging


MAXMIND_URL = 'http://geolite.maxmind.com/download/geoip/database/'
MAXMIND_FILENAME = 'GeoLite2-Country.mmdb.gz'
LOCAL_FILENAME = 'GeoLite2-Country.mmdb'
GEOIP_PATH = "/common/static/data/geoip/"


def match_md5(fp, md5_url):
    """

    Purpose of the method to make sure downloaded file is accurate.

    Args:
         fp (file): downloaded file
         md5_url (str): url to read md5 hash of file

    Returns:
        bool: Returns True if downloaded file hash and hash returned by url
        are same otherwise returns False

    """
    md5 = urllib.request.urlopen(md5_url).read()
    m = hashlib.md5()
    for line in fp:
        m.update(line)
    fp.seek(0)
    return m.hexdigest() == md5.decode()


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

    Downloads the file and check md5 hash to make sure file is downloaded correctly. If doesn't
    match then it would abort operation otherwise continue copying the file

    Args:
        current_directory: current process directory which would be edx-platform repo

    Returns:
        None

    Raises:
        ValueError: if md5 hash of downloaded file doesn't match

    """
    logging.info("Downloading maxmind geoip2 country database  ")
    downloaded_file = os.path.join(current_directory + GEOIP_PATH, MAXMIND_FILENAME)
    existing_file = os.path.join(current_directory + GEOIP_PATH, LOCAL_FILENAME)
    urllib.request.urlretrieve(
        urllib.parse.urljoin(MAXMIND_URL, MAXMIND_FILENAME),
        downloaded_file
    )
    logging.info("Downloading completed geoip2 country database  ")
    with gzip.open(downloaded_file, 'rb') as outfile:

        md5_url = urllib.parse.urljoin(
            MAXMIND_URL,
            MAXMIND_FILENAME.split('.', 1)[0] + '.md5'
        )
        if not match_md5(outfile, md5_url):
            logging.info("Downloaded file hash did't matched. Aborting the operation")
            try:
                os.remove(downloaded_file)
            finally:
                raise ValueError(
                    'md5 of %s doesn\'t match the signature.' % downloaded_file
                )
        write(outfile, existing_file)
    os.remove(downloaded_file)
