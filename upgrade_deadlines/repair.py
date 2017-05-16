#!/usr/bin/env python
import logging
import os

from dateutil.parser import parse
from edx_rest_api_client.client import EdxRestApiClient


logger = logging.getLogger(__name__)

OIDC_URL = os.environ.get('OIDC_URL', 'https://courses.edx.org/oauth2')
OIDC_KEY = os.environ.get('OIDC_KEY')
OIDC_SECRET = os.environ.get('OIDC_SECRET')
DISCOVERY_API_URL = os.environ.get('DISCOVERY_API_URL', 'https://prod-edx-discovery.edx.org/api/v1/')


class DiscoveryClient:
    def __init__(self):
        jwt, __ = EdxRestApiClient.get_oauth_access_token(
            f'{OIDC_URL}/access_token',
            OIDC_KEY,
            OIDC_SECRET,
            token_type='jwt'
        )

        self.client = EdxRestApiClient(DISCOVERY_API_URL, jwt=jwt)

    def load(self):
        empty_with_end = []
        empty_without_end = []
        upgrade_deadline_after_end = []

        querystring = {
            'page': 1,
            'page_size': 50,
        }

        next_page = True
        while next_page:
            number = querystring['page']
            logger.info(f'Requesting page {number}.')

            data = self.client.course_runs.get(**querystring)
            course_runs = data['results']
            next_page = data['next']
            if next_page:
                querystring['page'] += 1

            for course_run in course_runs:
                key = course_run['key']
                end = course_run['end']

                for seat in course_run['seats']:
                    upgrade_deadline = seat['upgrade_deadline']

                    if seat['type'] == 'verified' and not upgrade_deadline:
                        if end:
                            empty_with_end.append(key)
                        else:
                            empty_without_end.append(key)

                    if upgrade_deadline and end:
                        if parse(seat['upgrade_deadline']) > parse(course_run['end']):
                            upgrade_deadline_after_end.append(key)

        logger.info(
            f'{len(empty_with_end + empty_without_end)} verified seats are missing an upgrade deadline.'
        )

        logger.info(
            f'{len(empty_without_end)} of the runs linked to these seats are also missing an end date.'
        )

        logger.info(
            f'{len(upgrade_deadline_after_end)} runs have an upgrade deadline set after their end date.'
        )


if __name__ == '__main__':
    logging.basicConfig(
        style='{',
        format='{asctime} {levelname} {process} [{filename}:{lineno}] - {message}',
        level=logging.INFO
    )

    DiscoveryClient().load()
