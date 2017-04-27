# -*- coding: utf-8 -*-
from __future__ import unicode_literals


import datetime
import logging

from .constants import GFA_COURSE_RUN_LIST

REQUIRED_SEATS_TYPES = ['verified', 'professional']
DATE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class SailthruTranslationService(object):
    """This is the service that converts the data in edX into what Sailthru can consume"""
    def __init__(self, data_service, lms_root, fixups=None):
        self.data_service = data_service
        self.lms_root = lms_root
        self.fixups = fixups

    def _convert_date(self, data_store, key):
        """ Convert date from ISO 8601 (e.g. 2016-04-15T20:35:11.424818Z) to Sailthru format"""
        if not (data_store and key and data_store.get(key)):
            return None
        iso_date = data_store.get(key)
        try:
            if '.' in iso_date:
                return datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d")
            return datetime.datetime.strptime(iso_date, DATE_TIME_FORMAT).strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _convert_tag(self, tagtype, tag):
        """ Convert string to a valid sailthru tag and add type- to the front if specified"""
        if tag:
            resp = tag.replace(' & ', '-').replace(',', '').replace('.', '').replace(' ', '-').replace('--', '-')
            if tagtype:
                resp = tagtype + '-' + resp
            return resp
        return ''

    def _create_course_vars(self, course, course_run, url, site_name, program_dictionary=None):
        """ Generate 'vars' section of Sailthru data"""
        seat_priority = ['credit', 'professional', 'verified', 'no-id-professional', 'audit', 'honor']
        sailthru_content_vars = {
            'course_run': 1,
            'marketing_url': url,
            'course_id': course['key'],
            'course_run_id': course_run['key'],
        }

        for key in ['enrollment_end', 'enrollment_start', 'course_start', 'course_end']:
            date_value = self._convert_date(course_run, key.replace('course_', ''))
            if date_value:
                sailthru_content_vars[key] = date_value

        if site_name:
            sailthru_content_vars['site_name'] = site_name

        if course_run.get('pacing_type'):
            sailthru_content_vars['pacing_type'] = course_run['pacing_type']
        if course_run.get('content_language'):
            sailthru_content_vars['content_language'] = course_run['content_language']

        # figure out the price(s) and save as Sailthru vars
        if course_run.get('seats'):
            sailthru_content_vars['sku'] = self._return_sku(course_run.get('seats'))
            for seat in course_run['seats']:
                sailthru_content_vars['price_{}'.format(seat['type'])] = seat['price']
                sailthru_content_vars['currency_{}'.format(seat['type'])] = seat['currency']
                # Adding the course type with the precedence as
                # Credit, Professional, Verified, Audit so that if a course run have
                # multiple seat types the one with the higher precedence will be added
                # in course_type
                if not sailthru_content_vars.get('course_type', None) or \
                        seat_priority.index(sailthru_content_vars['course_type']) > seat_priority.index(seat['type']):
                    sailthru_content_vars['course_type'] = seat['type']

                # add upgrade deadline if there is one
                if seat.get('upgrade_deadline'):
                    deadline_key = 'upgrade_deadline_{}'.format(seat['type'])
                    sailthru_content_vars[deadline_key] = self._convert_date(seat, 'upgrade_deadline')

        if course_run['key'] in GFA_COURSE_RUN_LIST:
            sailthru_content_vars['course_type'] = 'gfa'

        # If the course runs have associated programs, also append programs information
        course_programs = course.get('programs')
        if course_programs and program_dictionary:
            sailthru_content_vars['programs'] = []
            for program_link in course_programs:
                program = program_dictionary.get(program_link.get('uuid'))
                if program:
                    sailthru_content_vars['programs'].append(self._translate_program(program))
                    sailthru_content_vars['course_type'] = program.get('type')

        return sailthru_content_vars

    def _get_tags_from_property(self, source_array, key, tag_prefix):
        tags = []
        if source_array:
            for tag_item in source_array:
                tags.append(self._convert_tag(tag_prefix, tag_item.get(key)))

        return tags

    def _return_sku(self, seats):
        """ Return dict of sku for a course run. """
        return {seat['type']: seat['sku'] for seat in seats if seat['type'] in REQUIRED_SEATS_TYPES}

    def translate_course_run(self, course_run, course, program_dictionary=None):
        # get marketing url
        url = course_run.get('marketing_url', course.get('marketing_url'))

        # create parameters for call to Sailthru
        sailthru_content = {
            'url': '{}/courses/{}/info'.format(self.lms_root, course_run.get('key')),
            'title': course_run.get('title'),
            'date': self._convert_date(course_run, 'modified'),
        }

        if course_run.get('short_description'):
            sailthru_content['description'] = course_run.get('short_description')

        # get first owner
        if course.get('owners') and len(course.get('owners')) > 0:
            sailthru_content['site_name'] = course['owners'][0]['key'].replace('_', ' ')

        # use enrollment_end for sailthru expire_date
        if course_run.get('enrollment_end'):
            sailthru_content['expire_date'] = self._convert_date(course_run, 'enrollment_end')
        elif course_run.get('end'):
            sailthru_content['expire_date'] = self._convert_date(course_run, 'end')

        # get the image, if any
        if course_run.get('image') and course_run['image']['src']:
            sailthru_content['images'] = {'thumb': {'url': course_run['image']['src']}}

        # create the interest tags
        tags = self._get_tags_from_property(course.get('subjects'), 'name', 'subject')
        tags.extend(self._get_tags_from_property(course.get('owners'), 'key', 'school'))
        tags.extend(self._get_tags_from_property(course.get('sponsors'), 'key', 'school'))

        if len(tags) > 0:
            sailthru_content['tags'] = ", ".join(tags)

        sailthru_content['vars'] = self._create_course_vars(
            course,
            course_run,
            url,
            sailthru_content.get('site_name'),
            program_dictionary,
        )
        sailthru_content['spider'] = 0

        # perform any fixups
        if self.fixups:
            for row in self.fixups:
                if row[0] == course_run['key']:
                    if row[1] == 'var':
                        logging.info('Changing var.%s to %s for %s', row[2], row[3], row[0])
                        sailthru_content['vars'][row[2]] = row[3]
                    else:
                        logging.info('Changing %s to %s for %s', row[2], row[3], row[0])
                        sailthru_content[row[2]] = row[3]

        return sailthru_content

    def translate_courses(self):
        sailthru_item_array = []
        course_run_count = 0
        marketable_course_run_count = 0
        courses = self.data_service.get_courses()
        marketable_run_keys = self.data_service.get_marketable_only_course_runs_keys()
        program_dictionary = self.data_service.get_program_dictionary()
        for course in courses:
            course_runs = course.get('course_runs', [])
            for course_run in course_runs:
                course_run_count += 1
                translated_course_run = self.translate_course_run(course_run, course, program_dictionary)
                if course_run.get('key') in marketable_run_keys:
                    # Mark the course_run to be marketable when updated through this script
                    translated_course_run['vars']['marketable'] = 1
                    marketable_course_run_count += 1
                sailthru_item_array.append(translated_course_run)

        logging.info(
            'Retrieved {} course_runs of which {} tagged marketable'.format(
                course_run_count,
                marketable_course_run_count
            )
        )
        return sailthru_item_array

    def _get_program_image_urls(self, program):
        card_image_url = program.get('card_image_url')
        banner_image = program.get('banner_image')
        banner_image_url = program.get('banner_image_url')
        if banner_image:
            banner_image_url = banner_image.get('large')['url']
        return card_image_url, banner_image_url

    def _filter_keys(self, collection, selected_keys):
        translated = []
        if collection:
            for item in collection:
                translated.append({key: item.get(key) for key in selected_keys})

        return translated

    def _translate_program_specific_data(self, program):

        card_image_url, banner_image_url = self._get_program_image_urls(program)

        data = {
            'marketing_url': program.get('marketing_url'),
            'uuid': program.get('uuid'),
            'type': program.get('type'),
            'banner_image_url': banner_image_url,
            'card_image_url': card_image_url,
            'authoring_organizations': self._filter_keys(
                program.get('authoring_organizations'),
                ['key', 'name', 'logo_image_url', 'marketing_url']
            ),
            'credit_backing_organizations': self._filter_keys(
                program.get('credit_backing_organizations'),
                ['key', 'name', 'logo_image_url', 'marketing_url']
            ),
            'corporate_endorsements': self._filter_keys(
                program.get('corporate_endorsements'),
                ['corporation_name', 'image']
            ),
            'subjects': self._filter_keys(
                program.get('subjects'),
                ['name', 'slug']
            )
        }

        return data

    def _translate_program(self, program):
        program_card_image, program_banner_image = self._get_program_image_urls(program)
        sailthru_item = {
            'title': program.get('title'),
            'url': program.get('marketing_url'),
            'images': {
                'thumb': {
                    'url': program_card_image or program_banner_image
                }
            },
            'description': program.get('subtitle'),
            # Do not respider of the content within a few minutes by Sailthru.
            # See https://getstarted.sailthru.com/new-for-developers-overview/horizon/content/
            'spider': 0,
        }

        tags = self._get_tags_from_property(program.get('subjects'), 'name', 'subjects')
        tags.extend(self._get_tags_from_property(program.get('authoring_organizations'), 'key', 'school'))
        tags.append(self._convert_tag(program.get('type').lower(), program.get('title')))

        if len(tags) > 0:
            sailthru_item['tags'] = ", ".join(tags)

        # now we get the vars
        sailthru_item['vars'] = self._translate_program_specific_data(program)

        return sailthru_item

    def _select_course_run_for_program(self, course):
        course_run_list = course.get('course_runs')
        if not course_run_list:
            return None

        default_start_string = '2030-12-31T00:00:00Z'
        sorted_course_runs = sorted(
            course_run_list,
            key=lambda run: datetime.datetime.strptime(
                run.get('start') or default_start_string,
                DATE_TIME_FORMAT
            )
        )
        for course_run in sorted_course_runs:
            if datetime.datetime.now() < datetime.datetime.strptime(
                course_run.get('start') or default_start_string,
                DATE_TIME_FORMAT
            ):
                return course_run
        return course_run_list[0]

    def _translate_program_course_runs(self, program):
        program_course_runs = []
        for course in program.get('courses'):
            course_run = self._select_course_run_for_program(course)
            if course_run:
                course_content = self.translate_course_run(course_run, course)
                program_course_runs.append(course_content)
        return program_course_runs

    def translate_programs(self):
        sailthru_item_array = []
        program_dictionary = self.data_service.get_program_dictionary()
        for program in program_dictionary.values():
            program_content = self._translate_program(program)
            program_content['vars']['course_runs'] = self._translate_program_course_runs(program)
            sailthru_item_array.append(program_content)

        return sailthru_item_array
