from faker import Factory

import responses

from services.sailthru_translation_service import SailthruTranslationService
from services.tests.catalog_api_test_mixins import CatalogApiTestMixins
from services.tests.fixtures import SINGLE_COURSE_DATA


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
            'site_name': u'HamiltonX',
            'description': u'.',
            'vars': {
                'price_audit': u'0.00',
                'site_name': u'HamiltonX',
                'course_run': True,
                'currency_verified': u'USD',
                'course_run_id': u'course-v1:HamiltonX+PHIL108x+3T2016',
                'pacing_type': u'instructor_paced',
                'currency_audit': u'USD',
                'course_id': u'HamiltonX+PHIL108x',
                'content_language': u'en-us',
                'price_verified': u'49.00',
                'course_start': '2016-10-18',
                'marketing_url': u'https://www.edx.org/course/ethics-sports-do-sports-morally-matter-hamiltonx-phil108x?utm_source=simonthebestedx&utm_medium=affiliate_partner'
            },
            'title': u'Ethics of Sports: Do Sports Morally Matter?',
            'url': '{root}/courses/{key}/info'.format(
                root=self.lms_root,
                key=SINGLE_COURSE_DATA['results'][0]['course_runs'][0]['key']
            ),
            'tags': u'subject-Education-Teacher-Training, subject-Philosophy-Ethics, subject-Health-Safety, school-HamiltonX',
            'spider': 0,
            'images': {
                'thumb': {
                    'url': u'https://www.edx.org/sites/default/files/course/image/promoted/phil108x_-_378x225.jpg'
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
