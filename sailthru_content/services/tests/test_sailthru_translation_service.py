from __future__ import unicode_literals

from faker import Factory
import ddt
import responses

from services.sailthru_translation_service import SailthruTranslationService
from services.tests.catalog_api_test_mixins import CatalogApiTestMixins
from services.tests.fixtures import SINGLE_COURSE_DATA


@ddt.ddt
class SailthruTranslationServiceTests(CatalogApiTestMixins):

    def setUp(self):
        super(SailthruTranslationServiceTests, self).setUp()
        self.faker = Factory.create()
        self.lms_root = 'http://' + self.faker.domain_name()
        self.sailthru_translation_service = SailthruTranslationService(
            self.catalog_api_service,
            self.lms_root)
        self.maxDiff = None

    @responses.activate
    def test_translate_courses(self):
        self.prepare_get_courses()
        self.prepare_get_programs()
        translated_course_runs = self.sailthru_translation_service.translate_courses()
        self.assertEqual(len(translated_course_runs), 1)
        expected_sailthru_item = {
            'site_name': 'HamiltonX',
            'description': '.',
            'vars': {
                'price_audit': '0.00',
                'site_name': 'HamiltonX',
                'course_run': True,
                'currency_verified': 'USD',
                'course_run_id': 'course-v1:HamiltonX+PHIL108x+3T2016',
                'pacing_type': 'instructor_paced',
                'currency_audit': 'USD',
                'course_id': 'HamiltonX+PHIL108x',
                'content_language': 'en-us',
                'price_verified': '49.00',
                'course_start': '2016-10-18',
                'marketing_url': 'https://www.edx.org/course/ethics-sports-do-sports-morally-matter-hamiltonx-phil108x?utm_source=simonthebestedx&utm_medium=affiliate_partner',
                'course_type': 'micromasters'
            },
            'title': 'Ethics of Sports: Do Sports Morally Matter?',
            'url': '{root}/courses/{key}/info'.format(
                root=self.lms_root,
                key=SINGLE_COURSE_DATA['results'][0]['course_runs'][0]['key']
            ),
            'tags': 'subject-Education-Teacher-Training, subject-Philosophy-Ethics, subject-Health-Safety, school-HamiltonX',
            'spider': 0,
            'images': {
                'thumb': {
                    'url': 'https://www.edx.org/sites/default/files/course/image/promoted/phil108x_-_378x225.jpg'
                }
            },
            'date': '2016-09-23'
        }
        self.assertDictEqual(translated_course_runs[0], expected_sailthru_item)

    @responses.activate
    def test_translate_programs(self):
        self.prepare_get_courses()
        self.prepare_get_programs()
        translated_programs = self.sailthru_translation_service.translate_programs()
        self.assertEqual(len(translated_programs), 1)
        self.assertEqual(len(translated_programs[0]['vars']['course_runs']), 4)

    def _get_expected_sailthru_item(self, seat_type=None):
        return {
            'site_name': 'HamiltonX',
            'description': '.',
            'vars': {
                'price_audit': '0.00',
                'site_name': 'HamiltonX',
                'course_run': True,
                'currency_verified': 'USD',
                'course_run_id': 'course-v1:HamiltonX+PHIL108x+3T2016',
                'pacing_type': 'instructor_paced',
                'currency_audit': 'USD',
                'course_id': 'HamiltonX+PHIL108x',
                'content_language': 'en-us',
                'price_verified': '49.00',
                'course_start': '2016-10-18',
                'marketing_url': 'https://www.edx.org/course/ethics-sports-do-sports-morally-matter-hamiltonx-phil108x?utm_source=simonthebestedx&utm_medium=affiliate_partner',
                'course_type': seat_type if seat_type else 'verified'
            },
            'title': 'Ethics of Sports: Do Sports Morally Matter?',
            'url': '{root}/courses/{key}/info'.format(
                root=self.lms_root,
                key=SINGLE_COURSE_DATA['results'][0]['course_runs'][0]['key']
            ),
            'tags': 'subject-Education-Teacher-Training, subject-Philosophy-Ethics, subject-Health-Safety, school-HamiltonX',
            'spider': 0,
            'images': {
                'thumb': {
                    'url': 'https://www.edx.org/sites/default/files/course/image/promoted/phil108x_-_378x225.jpg'
                }
            },
            'date': '2016-09-23'
        }

    @responses.activate
    @ddt.data(None, 'professional', 'credit')
    def test_translated_vars(self, seat_type):
        self.prepare_get_courses(seat_type)
        translated_course_runs = self.sailthru_translation_service.translate_courses()
        self.assertEqual(len(translated_course_runs), 1)
        self.assertDictEqual(translated_course_runs[0], self._get_expected_sailthru_item(seat_type))
