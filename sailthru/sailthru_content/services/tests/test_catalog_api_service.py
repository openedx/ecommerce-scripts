import responses

from sailthru.sailthru_content.services.tests.catalog_api_test_mixins import CatalogApiTestMixins
from sailthru.sailthru_content.services.tests.fixtures import (
    SINGLE_COURSE_DATA, SINGLE_PROGRAM_DATA, SINGLE_SEARCHABLE_COURSE_DATA
)


class CatalogApiServiceTests(CatalogApiTestMixins):
    def setUp(self):
        super(CatalogApiServiceTests, self).setUp()

    @responses.activate
    def test_get_courses(self):
        self.prepare_get_courses()
        courses = self.catalog_api_service.get_courses()
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(len(courses), SINGLE_COURSE_DATA['count'])
        self.assertDictEqual(courses[0], SINGLE_COURSE_DATA.get('results')[0])

    @responses.activate
    def test_get_program_dictionary(self):
        self.prepare_get_programs()
        program_dict = self.catalog_api_service.get_program_dictionary()
        self.assertEqual(len(program_dict.values()), SINGLE_PROGRAM_DATA['count'])
        expected_program = SINGLE_PROGRAM_DATA['results'][0]
        retrieved_program = program_dict.get(expected_program['uuid'])
        self.assertEqual(len(responses.calls), 1)
        self.assertIsNotNone(retrieved_program)
        self.assertEqual(retrieved_program, expected_program)

    @responses.activate
    def test_get_searchable_course_keys(self):
        self.prepare_searchable_courses()
        course_keys = self.catalog_api_service.get_searchable_course_run_keys()
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(course_keys[0], SINGLE_SEARCHABLE_COURSE_DATA['results'][0]['key'])
