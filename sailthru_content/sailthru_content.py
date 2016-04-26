#! /usr/bin/env python

""" Synchronize edX course catalog in to Sailthru. """

import logging
import datetime
import json
import sys
import os
import argparse
from edx_rest_api_client.client import EdxRestApiClient
from sailthru.sailthru_client import SailthruClient

logger = logging.getLogger(__name__)


def setup_logging():
    """ Setup logging.

    Add support for console logging, and avoid truncation by pandas.
    """
    msg_format = '%(asctime)s - %(levelname)s - %(message)s'
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(msg_format))
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)


def main(argv):
    parser = argparse.ArgumentParser(description='Sailthru course synch script')

    parser.add_argument(
            'command',
            choices=['list', 'load', 'clear'])

    parser.add_argument(
            '--access_token',
            default=os.environ.get('CONTENT_LOAD_ACCESS_TOKEN', None),
            help='OAuth2 access token used to authenticate API calls.'
        )

    parser.add_argument(
            '--oauth_host',
            default=os.environ.get('CONTENT_LOAD_OAUTH_HOST', 'https://courses.stage.edx.org/oauth2'),
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

    args = parser.parse_args()
    access_token = args.access_token

    # connect to Sailthru
    sc = SailthruClient(args.sailthru_key, args.sailthru_secret)

    # Process 'list' command
    if args.command == 'list':
        while True:
            response = sc.api_get('content', {'items': 1000})

            if not response.is_ok():
                logger.error("Error code %d connecting to Sailthru content api: %s",
                             response.json['error'], response.json['errormsg'])
                return

            for body in response.json['content']:
                logger.info(body)
            return

    # Process 'clear' command
    if args.command == 'clear':
        while True:
            response = sc.api_get('content', {})

            if not response.is_ok():
                logger.error("Error code %d connecting to Sailthru content api: %s",
                             response.json['error'],
                             response.json['errormsg'])
                return

            if not response.json['content']:
                logger.info('Content cleared')
                return

            for body in response.json['content']:
                response = sc.api_delete('content', {'url': body['url']})
                if response.is_ok():
                    logger.info("url %s deleted", body['url'])

    # Try to get edX access token if not supplied
    if not access_token:
        logger.info('No access token provided. Retrieving access token using client_credential flow...')

        try:
            access_token, __ = EdxRestApiClient.get_oauth_access_token(
                '{root}/access_token'.format(root=args.oauth_host),
                args.oauth_key,
                args.oauth_seret
            )
        except Exception:
            logger.exception('No access token provided or acquired through client_credential flow.')
            raise

    # logger.info('Token retrieved: %s', access_token)

    # use programs api to build table of course runs that are part of xseries
    series_table = {}

    page = 1
    while page:
        # TODO ***TEMP*** read from file until oauth bearer support in programs api
        try:
            with open("test%d.json" % page) as auth_file:
                response = json.load(auth_file)

                if response['next']:
                    page += 1
                else:
                    page = None

            for body in response['results']:
                index = 1
                for body2 in body['course_codes']:
                    for body3 in body2['run_modes']:
                        series_table[body3['course_key']] = {'series': body['id'], 'index': index}
                    index += 1
        except:
            logger.info("xseries data not available")
            page = None

    client = EdxRestApiClient(args.content_api_url, oauth_access_token=access_token)

    count = None
    page = 1
    course_runs = 0

    # read the courses and create a Sailthru content item for each course_run within the course

    while page:
        # get a page of courses
        response = client.courses().get(limit=20, offset=(page-1)*20)

        count = response['count']
        results = response['results']

        if response['next']:
            page += 1
        else:
            page = None

        for course in results:
            for course_run in course['course_runs']:

                sailthru_content = create_sailthru_content(course, course_run, series_table)

                if sailthru_content:
                    course_runs += 1

                    response = sc.api_post('content', sailthru_content)
                    if not response.is_ok():
                        logger.error("Error code %d connecting to Sailthru content api: %s",
                                     response.json['error'],
                                     response.json['errormsg'])
                        return

                    logger.info("Course: %s, Course_run: %s saved in Sailthru.", course['key'], course_run['key'])

    logger.info('Retrieved %d courses.', count)
    logger.info('Saved %d course runs in Sailthru.', course_runs)


def create_sailthru_content(course, course_run, series_table):
    # **temp** expected to move to course_run
    url = course['marketing_url']

    # skip course runs with no url
    if not url:
        return None

    # create parameters for call to Sailthru
    sailthru_content = {}
    sailthru_content_vars = {}
    sailthru_content['url'] = url
    sailthru_content['title'] = course_run['title']
    if course_run['short_description']:
        sailthru_content['description'] = course_run['short_description']
    sailthru_content_vars['course_id'] = course['key']
    sailthru_content_vars['course_run_id'] = course_run['key']

    # get first owner
    if course['owners'] and len(course['owners']) > 0:
        sailthru_content['site_name'] = course['owners'][0]['key']

    # use last modified date for sailthru 'date'
    sailthru_content['date'] = convert_date(course_run['modified'])

    # use enrollment_end for sailthru expire_date
    if course_run['enrollment_end']:
        sailthru_content['expire_date'] = convert_date(course_run['enrollment_end'])
        sailthru_content_vars['enrollment_end'] = convert_date(course_run['enrollment_end'])
    if course_run['enrollment_start']:
        sailthru_content_vars['enrollment_start'] = convert_date(course_run['enrollment_start'])
    if course_run['start']:
        sailthru_content_vars['course_start'] = convert_date(course_run['start'])
    if course_run['end']:
        sailthru_content_vars['course_end'] = convert_date(course_run['end'])

    # figure out the price(s) and save as Sailthru vars
    if course_run['seats']:
        for seat in course_run['seats']:
            sailthru_content_vars['price_%s' % seat['type']] = seat['price']
            sailthru_content_vars['currency_%s' % seat['type']] = seat['currency']
            # add upgrade deadline if there is one
            if seat['upgrade_deadline']:
                sailthru_content_vars['upgrade_deadline_%s' % seat['type']] = convert_date(seat['upgrade_deadline'])

    # get the image, if any
    if course_run['image'] and course_run['image']['src']:
        sailthru_content['images'] = {'thumb': {'url': course_run['image']['src']}}

    # create the interest tags
    tags = []
    if course['subjects']:
        for subject in course['subjects']:
            tags.append(convert_tag('subject', subject['name']))
    if course_run['instructors']:
        for instructor in course_run['instructors']:
            tags.append(convert_tag('instructor', instructor['name']))
    if course_run['staff']:
        for staff in course_run['staff']:
            tags.append(convert_tag('staff', staff['name']))
    if course['owners']:
        for owner in course['owners']:
            tags.append(convert_tag('school', owner['key']))
    if course['sponsors']:
        for sponsor in course['sponsors']:
            tags.append(convert_tag('school', sponsor['key']))
    # add interest tags for course id and course run id
    #   note, interest tags should contain only lower case chars and '-'
    trans = "".maketrans('+:./', '----')
    tags.append(convert_tag(None, course['key'].translate(trans)))
    tags.append(convert_tag(None, course_run['key'].translate(trans)))

    # check if course run is part of an xseries
    if course_run['key'] in series_table:
        sailthru_content_vars['series_id'] = series_table[course_run['key']]['series']
        sailthru_content_vars['series_index'] = series_table[course_run['key']]['index']

    if len(tags) > 0:
        sailthru_content['tags'] = ", ".join(tags)
    sailthru_content['vars'] = sailthru_content_vars
    sailthru_content['spider'] = 0
    return sailthru_content


def convert_date(iso_date):
    """ Convert date from ISO 8601 (e.g. 2016-04-15T20:35:11.424818Z) to Sailthru format
    :param iso_date:
    :return: sailthru format date
    """
    if iso_date is None:
        return None
    if '.' in iso_date:
        return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S +0000")
    return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S +0000")


def convert_tag(tagtype, tag):
    """ Convert string to a valid sailthru tag and add type- to the front
    :param tagtype: type of tag or None which leaves type and '-' off the front
    :param tag: tag string
    :return: valid tag
    """
    # TODO need to deal with chinese characters...
    if tag:
        resp = tag.replace(' & ', '-').replace(',', '').replace('.', '').replace(' ', '-').replace('--', '-').casefold()
        if tagtype:
            resp = tagtype + '-' + resp
        return resp
    return ''


if __name__ == "__main__":
    setup_logging()

    logger.info('Course synchronization started...')

    main(sys.argv[1:])
