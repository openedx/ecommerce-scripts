import json
import unittest

from faker import Factory
import responses


from services.catalog_api_service import CatalogApiService
from services.tests.fixtures import SINGLE_COURSE_DATA, SINGLE_PROGRAM_DATA


class CatalogApiTestMixins(unittest.TestCase):
    def setUp(self):
        faker = Factory.create()
        self.oauth_host = 'http://' + faker.domain_name()
        self.api_url_root = 'http://' + faker.domain_name()
        self.catalog_api_service = CatalogApiService(faker.password(), self.oauth_host, None, None, self.api_url_root)

    def prepare_get_courses(self):
        responses.add(
            responses.GET, self.api_url_root + '/courses/',
            body=json.dumps(SINGLE_COURSE_DATA),
            status=200,
            content_type='application/json',
            match_querystring=False
        )

    def prepare_get_programs(self):
        responses.add(
            responses.GET, self.api_url_root + '/programs/',
            body=json.dumps(SINGLE_PROGRAM_DATA),
            status=200,
            content_type='application/json',
            match_querystring=False
        )
