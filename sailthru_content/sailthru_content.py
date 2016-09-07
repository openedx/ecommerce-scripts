#! /usr/bin/env python

""" Synchronize edX course catalog in to Sailthru. """

import logging
import datetime
import json
import sys
import os
import argparse
import csv
import time
import tempfile

from edx_rest_api_client.client import EdxRestApiClient
from sailthru.sailthru_client import SailthruClient
from sailthru.sailthru_error import SailthruClientError

"""
A script intended to be run periodically (e.g. nightly) which uses the Course Discovery API to populate/update
the Sailthru content library.  Useful when Sailthru is used for email marketing. The script invocation syntax is
as follows:

 usage: sailthru_content.py [-h] [--access_token ACCESS_TOKEN]
                           [--oauth_host OAUTH_HOST] [--oauth_key OAUTH_KEY]
                           [--oauth_secret OAUTH_SECRET]
                           [--sailthru_key SAILTHRU_KEY]
                           [--sailthru_secret SAILTHRU_SECRET]
                           [--content_api_url CONTENT_API_URL]
                           [--lms_url LMS_URL]
                           [--email_report EMAIL_REPORT]
                           {list,batch,load,clear}

The 'clear' command deletes all the entries currently in the Sailthru content library.  It should generally only be
used during testing before deployment.  The 'list' command displays, in JSON, up to 1000 entries currently in the
Sailthru content library.  The 'load' command reads the course list using the Course Discovery API and adds/updates
the Sailthru content library appropriately.  The 'batch' command sends the updates to Sailthru as a batch job.  The
result is sent as a brief report to the address specified in --email_report.  Batch mode is the most efficient and
doesn't risk violating the api rate limiting in Sailthru.

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

To get access to the Course Discovery API, you need either an existing access token, or you can specify the
oauth_host, oauth_key and oauth_secret.

Sample command to load course content in batch:

sailthru_content.py --oauth_key=<api key> --oauth_secret=<api secret>
   --sailthru_key=<sailthru key> --sailthru_secret=<sailthru secret>
   --content_api_url=https://prod-edx-discovery.edx.org/api/v1/
   --lms_url=https://courses.edx.org
   --fixups=fixups.csv
   --email_report=somebody@edx.org batch

"""

logger = logging.getLogger(__name__)


def setup_logging():
    """ Setup logging.
    """
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')


def main(argv):

    args = get_args(argv)

    # connect to Sailthru
    sc = SailthruClient(args.sailthru_key, args.sailthru_secret)

    # Process 'list' command
    if args.command == 'list':
        process_list(sc)
    elif args.command == 'clear':
        process_clear(sc, False)
    elif args.command == 'cleanup':
        process_clear(sc, True)
    elif args.command == 'load':
        process_load(args, sc, args.lms_url, None)
    elif args.command == 'batch':
        if not args.email_report:
            logger.error("email_report option required with batch option.")
            exit(1)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            process_load(args, None, args.lms_url, tmp)
            tmp.close()
            upload_to_sailthru(tmp.name, args.email_report, sc)
            os.unlink(tmp.name)
    elif args.command == 'test':
        process_load(args, None, args.lms_url, None)


def process_list(sc):
    """ Process list command
    """

    response = sc.api_get('content', {'items': 1000})

    if not response.is_ok():
        logger.error("Error code %d connecting to Sailthru content api: %s",
                     response.json['error'], response.json['errormsg'])
        return

    for body in response.json['content']:
        logger.info(body)


def process_clear(sc, cleanup):
    """ Process clear command
    """

    while True:
        response = sc.api_get('content', {'items': 4000})

        if not response.is_ok():
            logger.error("Error code %d connecting to Sailthru content api: %s",
                         response.json['error'],
                         response.json['errormsg'])
            return

        if not response.json['content']:
            logger.info('Content cleared')
            return

        for body in response.json['content']:
            if not cleanup or len(body['tags']) == 0:

                response = sc.api_delete('content', {'url': body['url']})
                if response.is_ok():
                    logger.info("url %s deleted", body['url'])

        if cleanup:
            return


def process_load(args, sc, lms_url, temp_file):
    """ Process load command
    """

    # Try to get edX access token if not supplied
    access_token = args.access_token
    if not access_token:
        logger.info('No access token provided. Retrieving access token using client_credential flow...')

        try:
            access_token, expires = EdxRestApiClient.get_oauth_access_token(
                '{root}/access_token'.format(root=args.oauth_host),
                args.oauth_key,
                args.oauth_secret, token_type='jwt')
        except Exception:
            logger.exception('No access token provided or acquired through client_credential flow.')
            raise

    logger.info('Token retrieved: %s', access_token)

    # use programs api to build table of course runs that are part of xseries
    series_table = load_series_table()

    # load any fixups
    fixups = load_fixups(args.fixups)
    logger.info(fixups)

    client = EdxRestApiClient(args.content_api_url, jwt=access_token)

    count = None
    page = 1
    course_runs = 0

    # read the courses and create a Sailthru content item for each course_run within the course

    while page:
        # get a page of courses
        response = client.courses().get(limit=500, offset=(page-1)*500)

        count = response['count']
        results = response['results']

        if response['next']:
            page += 1
        else:
            page = None

        for course in results:
            for course_run in course['course_runs']:

                sailthru_content = create_sailthru_content(course, course_run, series_table, lms_url, fixups)

                if sailthru_content:
                    course_runs += 1

                    if sc:
                        try:
                            response = sc.api_post('content', sailthru_content)
                        except SailthruClientError as exc:
                            logger.exception("Exception attempting to update Sailthru", exc)
                            # wait 10 seconds and retry
                            time.sleep(10)
                            response = sc.api_post('content', sailthru_content)

                        if not response.is_ok():
                            logger.error("Error code %d connecting to Sailthru content api: %s",
                                         response.json['error'],
                                         response.json['errormsg'])
                            return

                        logger.info("Course: %s, Course_run: %s saved in Sailthru.", course['key'], course_run['key'])

                    elif temp_file:
                        json.dump(sailthru_content, temp_file)
                        temp_file.write('\n')
                        logger.info("Course: %s, Course_run: %s being updated.", course['key'], course_run['key'])

                    else:
                        logger.info(sailthru_content)

    logger.info('Retrieved %d courses.', count)
    logger.info('Saved %d course runs in Sailthru.', course_runs)


def create_sailthru_content(course, course_run, series_table, lms_url, fixups):

    # get marketing url
    url = course_run['marketing_url']
    if not url:
        url = course['marketing_url']

    # create parameters for call to Sailthru
    sailthru_content = {}
    sailthru_content['url'] = '{}/courses/{}/info'.format(lms_url, course_run['key'])
    sailthru_content['title'] = course_run['title']
    if course_run['short_description']:
        sailthru_content['description'] = course_run['short_description']

    # get first owner
    if course['owners'] and len(course['owners']) > 0:
        sailthru_content['site_name'] = course['owners'][0]['key'].replace('_', ' ')
        # Temporarily change Berkeley site name
        # TODO Remove ASAP
        if sailthru_content['site_name'] == "BerkeleyX":
            sailthru_content['site_name'] = "UC BerkeleyX"

    # use last modified date for sailthru 'date'
    sailthru_content['date'] = convert_date(course_run['modified'])

    # use enrollment_end for sailthru expire_date
    if course_run['enrollment_end']:
        sailthru_content['expire_date'] = convert_date(course_run['enrollment_end'])
    else:
        sailthru_content['expire_date'] = convert_date(course_run['end'])

    # get the image, if any
    if course_run['image'] and course_run['image']['src']:
        sailthru_content['images'] = {'thumb': {'url': course_run['image']['src']}}

    # create the interest tags
    tags = []
    if course['subjects']:
        for subject in course['subjects']:
            tags.append(convert_tag('subject', subject['name']))

    if course['owners']:
        for owner in course['owners']:
            tags.append(convert_tag('school', owner['key']))
    if course['sponsors']:
        for sponsor in course['sponsors']:
            tags.append(convert_tag('school', sponsor['key']))

    if len(tags) > 0:
        sailthru_content['tags'] = ", ".join(tags)
    sailthru_content['vars'] = _create_course_vars(course, course_run, url, series_table)
    sailthru_content['spider'] = 0

    # perform any fixups
    for row in fixups:
        if row[0] == course_run['key']:
            if row[1] == 'var':
                logger.info('Changing var.%s to %s for %s', row[2], row[3], row[0])
                sailthru_content['vars'][row[2]] = row[3]
            else:
                logger.info('Changing %s to %s for %s', row[2], row[3], row[0])
                sailthru_content[row[2]] = row[3]

    return sailthru_content


def _create_course_vars(course, course_run, url, series_table):
    """ Generate 'vars' section of Sailthru data
    """
    sailthru_content_vars = {}
    sailthru_content_vars['course_run'] = True
    sailthru_content_vars['marketing_url'] = url
    sailthru_content_vars['course_id'] = course['key']
    sailthru_content_vars['course_run_id'] = course_run['key']

    # use enrollment_end for sailthru expire_date
    if course_run['enrollment_end']:
        sailthru_content_vars['enrollment_end'] = convert_date(course_run['enrollment_end'])
    if course_run['enrollment_start']:
        sailthru_content_vars['enrollment_start'] = convert_date(course_run['enrollment_start'])
    if course_run['start']:
        sailthru_content_vars['course_start'] = convert_date(course_run['start'])
    if course_run['end']:
        sailthru_content_vars['course_end'] = convert_date(course_run['end'])
    if course_run['pacing_type']:
        sailthru_content_vars['pacing_type'] = course_run['pacing_type']
    if course_run['content_language']:
        sailthru_content_vars['content_language'] = course_run['content_language']

    # figure out the price(s) and save as Sailthru vars
    if course_run['seats']:
        for seat in course_run['seats']:
            sailthru_content_vars['price_%s' % seat['type']] = seat['price']
            sailthru_content_vars['currency_%s' % seat['type']] = seat['currency']
            # add upgrade deadline if there is one
            if seat['upgrade_deadline']:
                sailthru_content_vars['upgrade_deadline_%s' % seat['type']] = convert_date(seat['upgrade_deadline'])

    # check if course run is part of an xseries
    # TODO: current approach assumes a course run is only part of a single program
    if course_run['key'] in series_table:
        sailthru_content_vars['series_id'] = series_table[course_run['key']]['series']
        sailthru_content_vars['series_index'] = series_table[course_run['key']]['index']

    return sailthru_content_vars


def load_series_table():
    """
    use programs api to build table of course runs that are part of xseries
    """
    #
    series_table = {}

    # TBD

    return series_table


def load_fixups(filename):
    """
    Read list of fixups.

    The fixups file should be a three column csv with any fields that should be overriden

    Each line should have:
        course_run,field_name,value
    """

    if not filename:
        return []

    with open(filename, 'rb') as f:
        reader = csv.reader(f)
        return list(reader)


def convert_date(iso_date):
    """ Convert date from ISO 8601 (e.g. 2016-04-15T20:35:11.424818Z) to Sailthru format
    """
    if iso_date is None:
        return None
    if '.' in iso_date:
        return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d")
    return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")


def convert_datetime(iso_date):
    """ Convert date from ISO 8601 (e.g. 2016-04-15T20:35:11.424818Z) to Sailthru format
    """
    if iso_date is None:
        return None
    if '.' in iso_date:
        return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S +0000")
    return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S +0000")


def convert_tag(tagtype, tag):
    """ Convert string to a valid sailthru tag and add type- to the front if specified
    """
    if tag:
        resp = tag.replace(' & ', '-').replace(',', '').replace('.', '').replace(' ', '-').replace('--', '-')
        if tagtype:
            resp = tagtype + '-' + resp
        return resp
    return ''


def upload_to_sailthru(filepath, report_email, client):
    """
    Use Sailthru job API to upload all content as a batch job
    """
    logger.info("Uploading %s" % filepath)
    # Start the upload job
    request_data = {
            'job': 'content_update',
            'file': filepath,
            'report_email': report_email
        }
    response = client.api_post('job', request_data, {'file': 1})

    if response.is_ok():
        job_id = response.get_body().get("job_id")
        logger.info("Import job started on SailThru - JOB ID: " + job_id)

        # Keeping checking status until we find out that it's done
        while True:
            logger.info("waiting for import to complete...")
            time.sleep(10)
            response = client.api_get('job', {'job_id': job_id})
            if response.get_body().get("status") == "completed":
                return
    else:
        error = response.get_error()
        logger.error("Error: " + error.get_message())
        logger.error("Status Code: " + str(response.get_status_code()))
        logger.error("Error Code: " + str(error.get_error_code()))
        exit(1)


def get_args(argv):
    parser = argparse.ArgumentParser(description='Sailthru course synch script')

    parser.add_argument(
            'command',
            choices=['list', 'load', 'batch', 'clear', 'test', 'cleanup'])

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
            '--email_report',
            help='Email recipient for report with batch option.'
        )

    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()

    logger.info('Course synchronization started...')

    main(sys.argv[1:])
