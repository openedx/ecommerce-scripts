#! /usr/bin/env python

import sailthru_content

# test datetime converter
def test_convert_date():
    content = sailthru_content
    assert content.convert_date('2016-04-20T17:34:34.444460Z') == "2016-04-20 17:34:34 +0000"
    assert content.convert_date('2016-04-20T17:34:34Z') == "2016-04-20 17:34:34 +0000"


# test tag converter
def test_convert_tag():
    content = sailthru_content
    assert content.convert_tag('subject', 'Accounting & Finance,...') == 'subject-accounting-finance'


# test create sailthru content
def test_create_sailthru_content():
    content = sailthru_content

    course_id = "course/xxx"
    course_run_id = "TestX/course/xxx"
    title = "Writing Fiction for Computers"
    description = "Lots of laughs for your PC friends"
    owner = "TestX"
    owner_tag = "school-testx"
    date = "2016-04-20T17:34:34.360311Z"
    converted_date = "2016-04-20 17:34:34 +0000"
    enrollment_end_date = "2017-12-14T05:00:00Z"
    converted_enrollment_end_date = "2017-12-14 05:00:00 +0000"
    enrollment_start_date = "2017-11-14T05:00:00Z"
    converted_enrollment_start_date = "2017-11-14 05:00:00 +0000"
    course_start_date = "2017-11-14T05:00:00Z"
    converted_course_start_date = "2017-11-14 05:00:00 +0000"
    course_end_date = "2017-11-24T05:00:00Z"
    converted_course_end_date = "2017-11-24 05:00:00 +0000"
    image_url = "https://image.location.edx.org/image"
    series_id = '22'
    series_index = 11
    subject1 = "Computer Science"
    subject1_converted = 'subject-computer-science'
    subject2 = "Literature"
    subject2_converted = 'subject-literature'
    instructor1 = "Jack London"
    instructor1_converted = "instructor-jack-london"
    staff1 = "Jill G. Hillson"
    staff1_converted = "staff-jill-g-hillson"
    sponsor1 = "US Navy"
    sponsor1_converted = "school-us-navy"
    upgrade_deadline = "2016-04-22T17:34:34.360311Z"
    converted_upgrade_deadline = "2016-04-22 17:34:34 +0000"

    series_table = {course_run_id: {'series': series_id, 'index': series_index}}

    course_run = {
                    "course": course_id,
                    "key": course_run_id,
                    "title": title,
                    "short_description": description,
                    "full_description": None,
                    "start": course_start_date,
                    "end": course_end_date,
                    "enrollment_start": enrollment_start_date,
                    "enrollment_end": enrollment_end_date,
                    "announcement": None,
                    "image": {
                        "src": image_url,
                        "description": None,
                        "height": None,
                        "width": None
                    },
                    "video": {
                        "src": "http://www.youtube.com/watch?v=pmrqb692hj0",
                        "description": None,
                        "image": None
                    },
                    "seats": [
                        {
                            "type": "audit",
                            "price": "0.00",
                            "currency": "USD",
                            "upgrade_deadline": "2014-02-01T04:59:00Z",
                            "credit_provider": None,
                            "credit_hours": None
                        },
                        {
                            "type": "honor",
                            "price": "0.00",
                            "currency": "USD",
                            "upgrade_deadline": None,
                            "credit_provider": None,
                            "credit_hours": None
                        },
                        {
                            "type": "verified",
                            "price": "50.00",
                            "currency": "USD",
                            "upgrade_deadline": upgrade_deadline,
                            "credit_provider": None,
                            "credit_hours": None
                        }
                    ],
                    "content_language": None,
                    "transcript_languages": [],
                    "instructors": [
                        {
                            "key": "e592a2ed-140f-45a0-b67a-e1016457cf48",
                            "name": instructor1,
                            "title": "",
                            "bio": None,
                            "profile_image": {
                                "src": "https://a.b.com/image1.jpg",
                                "description": None,
                                "height": None,
                                "width": None
                            }
                        }
                    ],
                    "staff": [
                        {
                            "key": "e592a2ed-140f-45a0-b67a-e1016457cf48",
                            "name": staff1,
                            "title": "",
                            "bio": None,
                            "profile_image": {
                                "src": "https://a.b.com/image2.jpg",
                                "description": None,
                                "height": None,
                                "width": None
                            }
                        }
                    ],
                    "pacing_type": "instructor_paced",
                    "min_effort": None,
                    "max_effort": None,
                    "modified": date
                }

    course = {
            "key": course_id,
            "title": title,
            "short_description": description,
            "full_description": None,
            "level_type": None,
            "subjects": [
                {
                    "name": subject1
                },
                {
                    "name": subject2
                }
            ],
            "prerequisites": [],
            "expected_learning_items": [],
            "image": None,
            "video": None,
            "owners": [
                {
                    "key": owner,
                    "name": None,
                    "description": None,
                    "logo_image": None,
                    "homepage_url": None
                }
            ],
            "sponsors": [
                {
                    "key": sponsor1,
                    "name": None,
                    "description": None,
                    "logo_image": None,
                    "homepage_url": None
                }
            ],
            "modified": date,
            "course_runs": [
                course_run
            ],
            "marketing_url": 'http://www.hi.there'
        }

    response = content.create_sailthru_content(course, course_run, series_table)

    assert response['url'] == 'http://www.hi.there'
    assert response['title'] == title
    assert response['description'] == description
    assert response['vars']['course_id'] == course_id
    assert response['vars']['course_run_id'] == course_run_id
    assert response['site_name'] == owner
    assert response['date'] == converted_date
    assert response['expire_date'] == converted_enrollment_end_date
    assert response['vars']['enrollment_start'] == converted_enrollment_start_date
    assert response['vars']['enrollment_end'] == converted_enrollment_end_date
    assert response['vars']['course_start'] == converted_course_start_date
    assert response['vars']['course_end'] == converted_course_end_date
    assert response['images']['thumb']['url'] == image_url
    assert response['vars']['series_id'] == series_id
    assert response['vars']['series_index'] == series_index
    assert response['spider'] == 0

    # verify the tags
    tags = response['tags']
    assert len(tags) > 4
    assert subject1_converted in tags
    assert subject2_converted in tags
    assert instructor1_converted in tags
    assert staff1_converted in tags
    assert owner_tag in tags
    assert sponsor1_converted in tags

    # verify the prices
    assert response['vars']['price_audit'] == '0.00'
    assert response['vars']['price_honor'] == '0.00'
    assert response['vars']['price_verified'] == '50.00'
    assert response['vars']['currency_audit'] == 'USD'
    assert response['vars']['currency_honor'] == 'USD'
    assert response['vars']['currency_verified'] == 'USD'
    assert response['vars']['upgrade_deadline_verified'] == converted_upgrade_deadline
