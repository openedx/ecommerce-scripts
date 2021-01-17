#! /usr/bin/env python

""" Synchronize edX course catalog in to Sailthru. """

import logging
import datetime
import json
import sys
import os
import argparse

import MySQLdb

from edx_rest_api_client.client import EdxRestApiClient

"""
Creates historical purchase records from ecommerce database for upload to Sailthru using
job API. https://getstarted.sailthru.com/new-for-developers-overview/reporting/job/

Purchase/enroll records are formatted as specified in:
https://getstarted.sailthru.com/new-for-developers-overview/advanced-features/purchase/

Before creating the files with purchase records, the content option should be used to
create the course content information (vars, tags, ...) which is send with each purchase/enroll.

Sample command to save content:
 python sailthru_order_migrate_sql.py --oauth_key=oauth_key --oauth_secret=oauth_secret
    --content_api_url=https://prod-edx-discovery.edx.org/api/v1/
    --lms_url=https://courses.edx.org --content_save=content.sav content

Sample command to create files for upload:
 python sailthru_order_migrate_sql.py --mysql_host=prod-edx-ecommerce-replica-001....com
    --mysql_pass="sql password" --oauth_key=oauth_key
    --lms_url=https://courses.edx.org --content_save=content.sav --result_save=result_ load

"""

logger = logging.getLogger(__name__)
processed_orders = set()
last_date_placed = None


def setup_logging():
    """ Setup logging.
    """
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')


def main(argv):

    args = get_args(argv)

    if args.command == 'load':
        process_load(args, args.lms_url)
    if args.command == 'content':
        save_content(args)


def save_content(args):

    content_table = build_content_table(args.content_api_url, args.lms_url, _get_access_token(args))

    with open(args.content_save, 'w') as outfile:
        json.dump(content_table, outfile)


def process_load(args, lms_url):
    """ Process load command
    """

    ecommerce_db = MySQLdb.connect(host=args.mysql_host,
                                   user='read_only',
                                   passwd=args.mysql_pass,
                                   db='ecommerce',
                                   connect_timeout=10)

    if args.content_save:
        logger.info('Loading saved content table from %s', args.content_save)
        with open(args.content_save) as data_file:
            content_table = json.load(data_file)

    else:
        access_token = _get_access_token(args)
        content_table = build_content_table(args.content_api_url, lms_url, access_token)

    if len(content_table) == 0:
        logger.error("Unable to retrieve course information from Course Discovery API")
        return

    logger.info('Content table contains %s course runs', len(content_table))

    # max file size is 100 meg, each record is around 800 bytes
    max_orders = 100000

    # number of records to read in a block from mysql
    read_size = 50000

    current_orders = 0
    fileno = 1
    total = 0
    added = 0

    # starting date
    date = datetime.date(2016, 8, 16)
    # ending date
    last_date = datetime.date(2016, 8, 29)

    f = open(args.result_save + '1.txt', 'w')

    while date <= last_date:

        more = True
        offset = 0

        while more:
            # read the orders and create a purchase record for each
            results = get_orders(ecommerce_db, read_size, offset, date)
            if len(results) < read_size:
                more = False
            else:
                offset += read_size

            for row in results:
                email = row[0]
                number = row[1]
                date_placed = row[2]
                cost = row[3]
                mode = row[4]
                if not mode:
                    mode = 'audit'
                course_id = row[5]
                title = row[6]

                param = _build_purchase_parameters(email, number, date_placed, cost, mode,
                                                   course_id, title, content_table, lms_url)
                if param:
                    current_orders += 1
                    if current_orders > max_orders:
                        f.close()
                        fileno += 1
                        f = open(args.result_save + f'{fileno}.txt', 'w')
                        current_orders = 1
                    json.dump(param, f)
                    f.write('\n')
                    added += 1

        total += added
        logger.info(f"Date {date} done, added={added}, total={total}")
        added = 0
        date += datetime.timedelta(days=1)

    f.close()


def get_orders(ecommerce_db, limit, offset, date):
    date_low = date.strftime("%Y-%m-%d")
    date_high = (date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    sql = """SELECT
    u.email
    , o.number
    , o.date_placed
    , o.total_excl_tax
    , pav2.value_text AS 'mode'
    , pav.value_text AS 'course_id'
    , ol.title
FROM
    order_order o
    JOIN ecommerce_user u ON (o.user_id = u.id)
    JOIN order_line ol ON (ol.order_id = o.id)
    JOIN catalogue_productattributevalue pav ON (pav.product_id = ol.product_id)
    JOIN catalogue_productattribute pa ON (pa.id = pav.attribute_id AND pa.code = 'course_key')
    LEFT JOIN catalogue_productattributevalue pav2 ON (pav2.product_id = ol.product_id AND pav2.attribute_id = 3)
WHERE
    pav.value_text != 'edX/DemoX.1/2014' AND
    o.status = 'Complete' AND
    o.date_placed >= '{} 00:00:00' AND o.date_placed < '{} 00:00:00'
LIMIT {} OFFSET {};
""".format(date_low, date_high, limit, offset)

    cursor = ecommerce_db.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()

    logger.info(len(results))
    return results


def _build_purchase_parameters(email, number, date_placed, cost, mode, course_id, title, content_table, lms_url):
    """Build Sailthru purchase item object

    :return: purchase api parms https://getstarted.sailthru.com/new-for-developers-overview/advanced-features/purchase/
    """

    # get cost
    cost_in_cents = int(cost * 100)
    if cost_in_cents == 0:
        cost_in_cents = 100

    # build item description
    item = {
        'id': f'{course_id}-{mode}',
        'url': f'{lms_url}/courses/{course_id}/info',
        'price': cost_in_cents,
        'qty': 1,
        'title': title,
    }

    # pick up tags and other fields from content table, if there
    course_data = None
    if course_id in content_table:
        course_data = content_table[course_id]
    if course_data:

        # get tags
        if 'tags' in course_data:
            item['tags'] = course_data['tags']

        # add vars to item
        item['vars'] = dict(course_data.get('vars', {}), mode=mode, course_run_id=course_id)

    else:
        item['vars'] = dict(mode=mode, course_run_id=course_id)

    purchase = dict(email=email,
                    date=date_placed.strftime("%Y-%m-%d %H:%M:%S +0000"),
                    purchase_keys={'extid': number},
                    items=[item])

    return purchase


def build_content_table(content_api_url, lms_url, access_token):
    """
    Use Course Discovery API to build dict of course runs
    """
    logger.info("Retrieving course content, url=" + content_api_url)

    client = EdxRestApiClient(content_api_url, jwt=access_token)

    page = 1
    content_table = {}

    # read the courses and create a Sailthru content item for each course_run

    while page:
        # get a page of courses
        response = client.courses().get(limit=500, offset=(page-1)*500)
        results = response['results']

        if response['next']:
            page += 1
        else:
            page = None

        for course in results:
            for course_run in course['course_runs']:

                content_table[course_run['key']] = create_sailthru_content(course, course_run, lms_url)

    logger.info('Retrieved %d course runs.', len(content_table))
    return content_table


def create_sailthru_content(course, course_run, lms_url):

    # create parameters for call to Sailthru
    sailthru_content = {}
    sailthru_content_vars = {}
    sailthru_content['url'] = lms_url + '/courses/' + course_run['key'] + '/info'
    sailthru_content_vars['course_run'] = True
    sailthru_content['title'] = course_run['title']
    if course_run['short_description']:
        sailthru_content['description'] = course_run['short_description']
    sailthru_content_vars['course_id'] = course['key']
    sailthru_content_vars['course_run_id'] = course_run['key']

    # get first owner
    if course['owners'] and len(course['owners']) > 0:
        sailthru_content['site_name'] = course['owners'][0]['key'].replace('_', ' ')

    # use last modified date for sailthru 'date'
    sailthru_content['date'] = convert_date(course_run['modified'])

    # use enrollment_end for sailthru expire_date
    if course_run['enrollment_end']:
        sailthru_content['expire_date'] = convert_date(course_run['enrollment_end'])
        sailthru_content_vars['enrollment_end'] = convert_date(course_run['enrollment_end'])
    if course_run['enrollment_start']:
        sailthru_content_vars['enrollment_start'] = convert_date(course_run['enrollment_start'])
        logging.info(course_run['enrollment_start'])
    if course_run['start']:
        sailthru_content_vars['course_start'] = convert_date(course_run['start'])
    if course_run['end']:
        sailthru_content_vars['course_end'] = convert_date(course_run['end'])
    if course_run['pacing_type']:
        sailthru_content_vars['pacing_type'] = course_run['pacing_type']
    if course_run['content_language']:
        sailthru_content_vars['content_language'] = course_run['content_language']
    if len(course_run['transcript_languages']) > 0:
        logger.info('Transcript language: ' + course_run['transcript_languages'][0])

    # figure out the price(s) and save as Sailthru vars
    if course_run['seats']:
        for seat in course_run['seats']:
            sailthru_content_vars['price_%s' % seat['type']] = seat['price']
            sailthru_content_vars['currency_%s' % seat['type']] = seat['currency']
            # add upgrade deadline if there is one
            if seat['upgrade_deadline']:
                sailthru_content_vars['upgrade_deadline_%s' % seat['type']] = convert_date(seat['upgrade_deadline'])

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
        return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d")
    return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")


def convert_datetime(iso_date):
    """ Convert date from ISO 8601 (e.g. 2016-04-15T20:35:11.424818Z) to Sailthru format
    :param iso_date:
    :return: sailthru format date
    """
    if iso_date is None:
        return None
    if '.' in iso_date:
        return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S +0000")
    return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S +0000")


def parse_datetime(iso_date):
    """ Convert date from ISO 8601 (e.g. 2016-04-15T20:35:11.424818Z) to Sailthru format
    :param iso_date:
    :return: sailthru format date
    """
    if iso_date is None:
        return None
    if '.' in iso_date:
        return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%fZ")
    return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%SZ")


def convert_tag(tagtype, tag):
    """ Convert string to a valid sailthru tag and add type- to the front
    :param tagtype: type of tag or None which leaves type and '-' off the front
    :param tag: tag string
    :return: valid tag
    """
    if tag:
        resp = tag.replace(' & ', '-').replace(',', '').replace('.', '').replace(' ', '-').replace('--', '-').lower()
        if tagtype:
            resp = tagtype + '-' + resp
        return resp
    return ''


def get_args(argv):
    parser = argparse.ArgumentParser(description='Sailthru course synch script')

    parser.add_argument(
            'command',
            choices=['content', 'load'])

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
            '--mysql_host',
            default=os.environ.get('MYSQL_HOST', ''),
            help='Host address for ecommerce db replica.'
        )

    parser.add_argument(
            '--mysql_pass',
            default=os.environ.get('MYSQL_HOST', ''),
            help='Password for ecommerce db replica.'
        )

    parser.add_argument(
            '--content_save',
            help='File where course content is saved.'
    )

    parser.add_argument(
            '--result_save',
            help='File where result is saved.'
    )

    return parser.parse_args()


def _get_access_token(args):
    access_token = args.access_token
    if not access_token:
        logger.info('No access token provided. Retrieving access token using client_credential flow...')

        try:
            access_token, expires = EdxRestApiClient.get_oauth_access_token(
                f'{args.oauth_host}/access_token',
                args.oauth_key,
                args.oauth_secret, token_type='jwt')
        except Exception:
            logger.exception('No access token provided or acquired through client_credential flow.')
            raise

    logger.info('Token retrieved: %s', access_token)
    return access_token


if __name__ == "__main__":
    setup_logging()

    logger.info('Order synchronization started...')

    main(sys.argv[1:])
