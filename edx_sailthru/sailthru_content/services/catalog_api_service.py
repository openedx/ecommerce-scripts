import logging
from urllib.parse import urlparse, parse_qs

from edx_rest_api_client.client import EdxRestApiClient

logger = logging.getLogger()
COURSES_PAGE_SIZE = 100
PROGRAMS_PAGE_SIZE = 40


class CatalogApiService(object):
    """The service to interface with edX catalog API"""

    def __init__(self, access_token, oauth_host, oauth_key, oauth_secret, api_url_root):
        self.access_token = access_token
        if not access_token:
            logger.info('No access token provided. Retrieving access token using client_credential flow...')
            try:
                access_token_url = '{}/access_token'.format(oauth_host)
                self.access_token, __ = EdxRestApiClient.get_oauth_access_token(
                    access_token_url, oauth_key, oauth_secret, token_type='jwt'
                )
            except Exception:
                logger.exception('No access token provided or acquired through client_credential flow.')
                raise

            logger.info('Retrieved access token.')

        self.api_client = EdxRestApiClient(api_url_root, jwt=self.access_token)
        self._programs_dictionary = {}

    def _get_resource_from_api(self, api_endpoint, **kwargs):
        results = []

        while True:
            response = api_endpoint.get(**kwargs)
            next_url = response.get('next')
            results.extend(response.get('results'))
            if next_url:
                parsed_url = urlparse(next_url)
                query_string_dict = parse_qs(parsed_url.query)
                kwargs = query_string_dict
            else:
                break

        return results

    def get_courses(self):
        logger.debug('Get Courses called')
        return self._get_resource_from_api(
            self.api_client.courses(),
            page=1,
            page_size=COURSES_PAGE_SIZE,
            exclude_utm=1
        )

    def get_marketable_only_course_runs_keys(self):
        logger.debug('Get marketable only course_runs called')
        courses = self._get_resource_from_api(
            self.api_client.courses(),
            page=1,
            page_size=COURSES_PAGE_SIZE,
            exclude_utm=1,
            marketable_course_runs_only=1,
        )
        course_run_keys = []
        for course in courses:
            course_runs = course.get('course_runs', [])
            for course_run in course_runs:
                course_run_keys.append(course_run.get('key'))

        logging.debug('Retrieved {} marketable course runs'.format(len(course_run_keys)))
        return course_run_keys

    def get_program_dictionary(self):
        if not self._programs_dictionary:
            program_array = self._get_resource_from_api(
                self.api_client.programs(),
                page=1,
                page_size=PROGRAMS_PAGE_SIZE,
                marketable_course_runs_only=1
            )
            for program in program_array:
                self._programs_dictionary[program['uuid']] = program
        return self._programs_dictionary
