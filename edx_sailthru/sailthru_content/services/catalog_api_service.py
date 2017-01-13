import logging

from edx_rest_api_client.client import EdxRestApiClient


logger = logging.getLogger()
COURSES_PAGE_SIZE = 500
PROGRAMS_PAGE_SIZE = 40


class CatalogApiService(object):
    """The service to interface with edX catalog API"""

    def __init__(self, access_token, oauth_host, oauth_key, oauth_secret, api_url_root):
        self.access_token = access_token
        if not access_token:
            logger.info('No access token provided. Retrieving access token using client_credential flow...')
            try:
                self.access_token, expires = EdxRestApiClient.get_oauth_access_token(
                    '{root}/access_token'.format(root=oauth_host),
                    oauth_key,
                    oauth_secret, token_type='jwt'
                )
            except Exception:
                logger.exception('No access token provided or acquired through client_credential flow.')
                raise

            logger.info('Token retrieved: %s', access_token)

        self.api_client = EdxRestApiClient(api_url_root, jwt=self.access_token)
        self._programs_dictionary = {}

    def _get_resource_from_api(self, api_endpoint, page_size, **kwargs):
        page = 0
        results = []

        while page >= 0:
            response = api_endpoint.get(limit=page_size, offset=(page * page_size), **kwargs)
            if response.get('next'):
                page += 1
            else:
                page = -1
            results.extend(response.get('results'))

        return results

    def get_courses(self):
        logger.debug('Get Courses called')
        return self._get_resource_from_api(self.api_client.courses(), COURSES_PAGE_SIZE, marketable=1, exclude_utm=1)

    def get_searchable_course_run_keys(self):
        logger.debug('Get Searchable Course runs called')
        searchable_course_keys = []
        searchable_course_runs = self._get_resource_from_api(
            self.api_client.course_runs(), COURSES_PAGE_SIZE, hidden=False, marketable=1
        )
        for course_run in searchable_course_runs:
            if course_run.get('key'):
                searchable_course_keys.append(course_run.get('key'))

        return searchable_course_keys

    def get_program_dictionary(self):
        if not self._programs_dictionary:
            program_array = self._get_resource_from_api(
                self.api_client.programs(),
                PROGRAMS_PAGE_SIZE,
                marketable=1,
                published_course_runs_only=1
            )
            for program in program_array:
                self._programs_dictionary[program['uuid']] = program
        return self._programs_dictionary
