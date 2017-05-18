#!/usr/bin/env python
import datetime
import logging
import os
from collections import namedtuple
from time import sleep

import dryscrape
from dateutil.parser import parse
from edx_rest_api_client.client import EdxRestApiClient


logger = logging.getLogger(__name__)

Run = namedtuple('Run', ['key', 'upgrade_deadline', 'end'])

OIDC_URL = os.environ.get('OIDC_URL', 'https://courses.edx.org/oauth2')
OIDC_KEY = os.environ.get('OIDC_KEY')
OIDC_SECRET = os.environ.get('OIDC_SECRET')

DISCOVERY_API_URL = os.environ.get('DISCOVERY_API_URL', 'https://prod-edx-discovery.edx.org/api/v1/')
ECOMMERCE_URL = os.environ.get('ECOMMERCE_URL', 'https://ecommerce.edx.org')

LMS_EMAIL = os.environ.get('LMS_EMAIL')
LMS_PASSWORD = os.environ.get('LMS_PASSWORD')


class DiscoveryClient:
    """
    Interface to the discovery service.
    """
    def __init__(self):
        jwt, __ = EdxRestApiClient.get_oauth_access_token(
            f'{OIDC_URL}/access_token',
            OIDC_KEY,
            OIDC_SECRET,
            token_type='jwt'
        )

        self.client = EdxRestApiClient(DISCOVERY_API_URL, jwt=jwt)

        self.deadline_empty_with_end = []
        self.deadline_empty_without_end = []
        self.deadline_after_end = []

    def load_runs(self):
        """
        Load runs from the discovery service, classifying them based on their
        upgrade deadlines and end dates.
        """
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
                            run = Run(key, None, parse(end))
                            self.deadline_empty_with_end.append(run)
                        else:
                            run = Run(key, None, None)
                            self.deadline_empty_without_end.append(run)

                    if upgrade_deadline and end:
                        parsed_upgrade_deadline = parse(seat['upgrade_deadline'])
                        parsed_end = parse(end)

                        if parsed_upgrade_deadline > parsed_end:
                            run = Run(key, parsed_upgrade_deadline, parsed_end)
                            self.deadline_after_end.append(run)

        empty_deadline_count = len(self.deadline_empty_with_end + self.deadline_empty_without_end)
        logger.info(
            f'{empty_deadline_count} verified seats are missing an upgrade deadline.'
        )

        count = len(self.deadline_empty_without_end)
        logger.info(
            f'{count} of the runs linked to these seats are also missing an end date:'
        )

        for run in self.deadline_empty_without_end:
            logger.info(run.key)

        count = len(self.deadline_after_end)
        logger.info(
            f'{count} runs have an upgrade deadline set after their end date:'
        )

        for run in self.deadline_after_end:
            logger.info(
                f'{run.key} ends at {run.end}, but has a verified seat with upgrade deadline set to {run.upgrade_deadline}'
            )


class CatClient:
    """
    Interface to the ecommerce service's course admin tool (CAT).
    """
    def __init__(self):
        self.cat_path = '/courses'

        dryscrape.start_xvfb()
        self.session = dryscrape.Session(base_url=ECOMMERCE_URL)

        # No need to load images.
        self.session.set_attribute('auto_load_images', False)

    def login(self):
        """
        Log in to the ecommerce service.
        """
        logger.info('Logging in to CAT.')

        self.session.visit(self.cat_path)

        # Wait for the LMS login page to render.
        self.session.wait_for(lambda: self.session.at_css('#login-form'))

        email_input_selector = '#login-email'
        password_input_selector = '#login-password'
        login_button_selector = '.login-button'

        self.session.at_css(email_input_selector).set(LMS_EMAIL)
        self.session.at_css(password_input_selector).set(LMS_PASSWORD)
        self.session.at_css(login_button_selector).click()

        # Wait for the CAT to render.
        self.session.wait_for(lambda: self.session.at_css('#app'))

    def update_run(self, key, deadline, *, dry=True):
        """
        Update a run's upgrade deadline.

        Arguments:
            key (str): Key identifying the course run to update.
            deadline (datetime.datetime): Upgrade deadline to set for the given run.

        Keyword Arguments:
            dry (bool): Whether to persist changes to the CAT (i.e., ecommerce and LMS).
                You must explicitly indicate when to write data.
        """
        self.session.visit(f'{self.cat_path}/{key}/edit')

        deadline_input_selector = '#expires'
        save_button_selector = '.btn-primary'
        edit_button_selector = '.btn-small'

        # Wait for the upgrade deadline input to render.
        self.session.wait_for(lambda: self.session.at_css(deadline_input_selector))

        formatted_deadline = deadline.strftime('%Y-%m-%dT%H:%M:%S')

        if dry:
            logger.info(f'This is a dry run. Would have set upgrade deadline for {key} to {formatted_deadline}.')
        else:
            logger.info(f'Setting upgrade deadline for {key} to {formatted_deadline}.')

            self.session.at_css(deadline_input_selector).set(formatted_deadline)

            # Save and wait for completion.
            self.session.at_css(save_button_selector).click()
            self.session.wait_for(lambda: self.session.at_css(edit_button_selector))

        # Respect the ecommerce service's 50/minute rate limit. Sleeping for
        # 60 / 50 = 1.2 seconds at a time is an easy way to maximize the number of
        # requests we can make while staying under the rate limit.
        sleep(60 / 50)


if __name__ == '__main__':
    logging.basicConfig(
        style='{',
        format='{asctime} {levelname} {process} [{filename}:{lineno}] - {message}',
        level=logging.INFO
    )

    discovery = DiscoveryClient()
    discovery.load_runs()

    cat = CatClient()
    cat.login()

    total = len(discovery.deadline_empty_with_end)
    logger.info(f'Setting upgrade deadlines for {total} runs.')

    tally = 0
    for run in discovery.deadline_empty_with_end:
        new_deadline = run.end - datetime.timedelta(days=10)

        try:
            cat.update_run(run.key, new_deadline, dry=True)
        except:
            logger.exception(f'There was a problem updating run {run.key}. Continuing.')

        tally += 1
        logger.info(f'{tally}/{total} runs updated.')
