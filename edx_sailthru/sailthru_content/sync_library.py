#! /usr/bin/env python

""" module to synchronize Sailthru Content Library with edX data in catalog """
import argparse
import csv
import logging
import json
import os
import sys

from services.catalog_api_service import CatalogApiService
from services.sailthru_api_service import SailthruApiService
from services.sailthru_translation_service import SailthruTranslationService


"""
A script intended to be run periodically (e.g. nightly) which uses the Course Discovery API to populate/update
the Sailthru content library for programs.  Useful when Sailthru is used for email marketing.
The script invocation syntax is as follows:

 usage: refresh_programs.py [-h] [--access_token ACCESS_TOKEN]
                           [--oauth_host OAUTH_HOST] [--oauth_key OAUTH_KEY]
                           [--oauth_secret OAUTH_SECRET]
                           [--sailthru_key SAILTHRU_KEY]
                           [--sailthru_secret SAILTHRU_SECRET]
                           [--content_api_url CONTENT_API_URL]
                           [--lms_url LMS_URL]
                           [--email_report EMAIL_REPORT]
                           [--type [programs, courses, all]]
                           {list,upload,clear,preview}

The 'clear' command deletes all the entries currently in the Sailthru content library.  It should generally only be
used during testing before deployment.  The 'list' command displays, in JSON, up to 1000 entries currently in the
Sailthru content library.  The 'upload' command sends the desired programs and/or courses to Sailthru as a batch job.
The result is sent as a brief report to the address specified in --email_report.

The following options are available:

+--------------------------------+-------------------------------------------------------+
| Switch                         | Purpose                                               |
+================================+=======================================================+
| --access_token                 | An access token for the Course Discovery API          |
+--------------------------------+-------------------------------------------------------+
| --oauth_host                   | The host used to obtain Course Discovery access token |
+--------------------------------+-------------------------------------------------------+
| --oauth_key                    | Key used to obtain Course Discovery access token      |
+--------------------------------+-------------------------------------------------------+
| --oauth_secret                 | Secret used to obtain Course Discovery access token   |
+--------------------------------+-------------------------------------------------------+
| --sailthru_key                 | Access key for Sailthru api                           |
+--------------------------------+-------------------------------------------------------+
| --sailthru_secret              | Access secret for Sailthru api                        |
+--------------------------------+-------------------------------------------------------+
| --content_api_url              | Url of Course Discovery API                           |
+--------------------------------+-------------------------------------------------------+
| --lms_url                      | Url of LMS (default http://courses.edx.org            |
+--------------------------------+-------------------------------------------------------+
| --email_report                 | Email address to sent batch report to                 |
+--------------------------------+-------------------------------------------------------+
| --type                         | A choice of "programs", "courses" or "all"            |
+--------------------------------+-------------------------------------------------------+

To get access to the Course Discovery API, you need either an existing access token, or you can specify the
oauth_host, oauth_key and oauth_secret.

Sample command to load course content in batch:

sync_library.py --oauth_key=<api key> --oauth_secret=<api secret>
   --oauth_host=https://api.edx.org/oauth2/v1
   --sailthru_key=<sailthru key> --sailthru_secret=<sailthru secret>
   --content_api_url=https://prod-edx-discovery.edx.org/api/v1/
   --lms_url=https://courses.edx.org
   --fixups=fixups.csv
   --type=courses
   --email_report=somebody@edx.org
   upload

"""


def setup_logging():
    """ Setup logging """
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)


def load_fixups(filename):
    """
    Read list of fixups.

    The fixups file should be a three column csv with any fields that should be overriden

    Each line should have:
        course_run,field_name,value
    """

    if not filename:
        return []

    with open(filename, 'rt') as f:
        reader = csv.reader(f)
        return list(reader)


def main(argv):

    args = get_args(argv)

    sailthru_service = SailthruApiService(args.sailthru_key, args.sailthru_secret, args.lms_url)
    if args.command == 'list':
        sailthru_service.list()
    elif args.command in ('upload', 'preview'):
        fixups_collection = None
        if args.fixups:
            fixups_collection = load_fixups(args.fixups)

        catalog_api_service = CatalogApiService(
            args.access_token,
            args.oauth_host,
            args.oauth_key,
            args.oauth_secret,
            args.content_api_url
        )

        translation_service = SailthruTranslationService(catalog_api_service, args.lms_url, fixups_collection)

        sailthru_items = []
        if args.type in ('courses', 'all'):
            sailthru_items.extend(translation_service.translate_courses())

        if args.type in ('programs', 'all'):
            sailthru_items.extend(translation_service.translate_programs())

        if args.command == 'upload':
            sailthru_service.upload(sailthru_items, args.report_email)
        else:
            print(json.dumps(sailthru_items))

    elif args.command == 'clear':
        sailthru_service.clear()
    else:
        pass


def get_args(argv):
    parser = argparse.ArgumentParser(description='Sailthru content library synchronize script')

    parser.add_argument(
        'command',
        choices=['list', 'upload', 'clear', 'preview'])

    parser.add_argument(
        '--type',
        help='The types of data to synchronize with sailthru. Choices are ["programs", "courses", "all"]'
    )

    parser.add_argument(
        '--access_token',
        default=os.environ.get('CONTENT_LOAD_ACCESS_TOKEN', None),
        help='OAuth2 access token used to authenticate API calls.'
    )

    parser.add_argument(
        '--oauth_host',
        default=os.environ.get('CONTENT_LOAD_OAUTH_HOST', 'https://api.edx.org/oauth2/v1'),
        help='OAuth2 base url.'
    )

    parser.add_argument(
        '--oauth_key',
        default=os.environ.get('CONTENT_LOAD_OAUTH_KEY', None),
        help='OAuth2 key used to authenticate Course Content API calls.'
    )

    parser.add_argument(
        '--oauth_secret',
        default=os.environ.get('CONTENT_LOAD_OAUTH_SECRET', None),
        help='OAuth2 secret token used to authenticate Course Content API calls.'
    )

    parser.add_argument(
        '--sailthru_key',
        default=os.environ.get('CONTENT_LOAD_SAILTHRU_KEY', None),
        help='Sailthru access key.'
    )

    parser.add_argument(
        '--sailthru_secret',
        default=os.environ.get('CONTENT_LOAD_SAILTHRU_SECRET', None),
        help='Sailthru access secret.'
    )

    parser.add_argument(
        '--content_api_url',
        default=os.environ.get('CONTENT_LOAD_API_URL', None),
        help='Content api url.'
    )

    parser.add_argument(
        '--lms_url',
        default=os.environ.get('CONTENT_LOAD_LMS_URL', 'https://courses.edx.org'),
        help='LMS url for course pages (e.g. https://courses.edx.org).'
    )

    parser.add_argument(
        '--fixups',
        help='CSV file with fields to fix (each line has course_run,field,value.'
    )

    parser.add_argument(
        '--report_email',
        help='Email recipient for report with batch option.'
    )

    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()

    logging.info('Content Library synchronize started...')

    main(sys.argv[1:])
