"""
Retrieve all financial aid submissions from Zendesk.
"""
from __future__ import unicode_literals

import codecs
import json
import logging
import os
import re
from io import open

from zendesk import Zendesk

logger = logging.getLogger(__name__)


def setup_logging():
    """ Setup logging.

    Add support for console logging
    """
    msg_format = '%(asctime)s - %(levelname)s - %(message)s'
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(msg_format))
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)


# setup_logging()

username = os.environ['USERNAME']
password = os.environ['PASSWORD']
zendesk = Zendesk('https://edxsupport.zendesk.com', username, password, api_version=2)


def parse_request(body):
    """
    Parse the content of a financial assistance request.
    """

    # Make sure the body begins with some expected text.
    if not body.startswith('Additional information:'):
        return None

    fields = {
        'username': 'Username',
        'full_name': 'Full Name',
        'annual_household_income': 'Annual Household Income',
        'country': 'Country',
        'allowed_for_marketing': 'Allowed for marketing purposes',
        'course_id': 'Course ID',
        'client_ip': 'Client IP'
    }

    try:
        request = {}

        for field, display_value in fields.iteritems():
            logger.debug('Searching for %s...', display_value)
            matches = re.search(r'{}: (.*)'.format(display_value), body, re.MULTILINE | re.IGNORECASE)
            request[field] = matches.group(1)

        return request
    except:
        print('Failed to parse...{}'.format(body))
        return None


# Find all financial assistance tickets
# Note (CCB): We seem to be creating tickets improperly. Instead of adding the prompt responses to the
# ticket description, they are added as a comment. Thus, we must retrieve data by first finding all tagged
# tickets, and then looking at the comments for each ticket. Eww.
page = 1
requests = []

while page:
    # Search for all tickets
    response = zendesk.search(query='type:ticket tags:financial_assistance', page=page)

    # Get the comments for each ticket and find the request details
    for ticket in response['results']:
        comments = zendesk.list_ticket_comments(ticket_id=ticket['id'])['comments']

        for comment in comments:
            request = parse_request(comment['body'])
            if request:
                requests.append(request)

    if response['next_page']:
        page += 1
    else:
        page = None

# Dump the data to a JSON file
json.dump(requests, codecs.open('requests.json', 'w', 'utf-8'), indent=2)
