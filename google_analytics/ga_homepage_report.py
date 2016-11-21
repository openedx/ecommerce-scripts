import argparse
from datetime import datetime, timedelta
import httplib2
import sys

from apiclient.discovery import build
from oauth2client import client, file, tools
from pandas import DataFrame, ExcelWriter, merge, concat, to_numeric
import xlsxwriter

################################################################
#
# Run this script by providing the following inputs
#     python ga_homepage_report.py yyyy-mm-dd yyyy-mm-dd /path/to/report/destination/
#
# The first argument is the start date
# The second argument is the end date
# The third argument is the location the report will be written to
#
###############################################################

def get_service():
    """Get a service that communicates to a Google API."""
    api_name = 'analytics'
    api_version = 'v3'
    scope = ['https://www.googleapis.com/auth/analytics.readonly']
    client_secrets_path = 'client_secrets.json'

    # Parse command-line arguments.
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[tools.argparser])
    flags = parser.parse_args([])

    # Set up a Flow object to be used if we need to authenticate.
    flow = client.flow_from_clientsecrets(
        client_secrets_path,
        scope=scope,
        message=tools.message_if_missing(client_secrets_path)
    )

    # Prepare credentials, and authorize HTTP object with them.
    # If the credentials don't exist or are invalid run through the native client
    # flow. The Storage object will ensure that if successful the good
    # credentials will get written back to a file.
    storage = file.Storage(api_name + '.dat')
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = tools.run_flow(flow, storage, flags)
    http = credentials.authorize(http=httplib2.Http())

    # Build the service object.
    service = build(api_name, api_version, http=http)

    return service


def _featuredCardDrivenEnrollments(date, enrollment_events, featured_card_click):
    # RETURN total events & unique events
    # GROUPED BY date, label (course/program id), card index
    # FOR anyone who clicked a certain featured card
    # AND whose session sequence was
    #     featured card click EVENTUALLY FOLLOWED BY
    #     a set of enrollment events
    service = get_service()

    data = service.data().ga().get(
        ids='ga:' + '86300562',
        start_date=str(date),
        end_date=str(date),
        max_results=10000,
        metrics='ga:totalEvents,ga:uniqueEvents',
        dimensions='ga:date,ga:eventLabel,ga:dimension5',
        filters=featured_card_click,
        segment='sessions::sequence::{featured_card_click};->>{enrollment_events}'.format(
            featured_card_click=featured_card_click,
            enrollment_events=enrollment_events
        )
    ).execute()

    return data.get('rows', [])


def featuredProgramCardDrivenProgramEnrollments(date):
    program_enrollment_events = ','.join([
        'ga:eventAction==edx.bi.user.course-details.enrolled-user.enroll-card',  # New MicroMaster
        'ga:eventAction==edx.bi.user.course-details.enroll.enroll-card',  # New xSeries
        'ga:eventAction==edx.bi.user.course-details.enroll.discovery-card',  # Old MicroMaster
        'ga:eventAction==edx.bi.user.xseries-details.enroll.discovery-card',  # Old xSeries
    ])

    featured_program_card_click = ';'.join([
        'ga:eventAction==edx.bi.user.discovery.card.click',
        'ga:eventCategory==program',
        'ga:dimension6==true',
        'ga:pagePath==/',
    ])

    return _featuredCardDrivenEnrollments(date, program_enrollment_events, featured_program_card_click)


def featuredProgramCardDrivenCourseEnrollments(date):
    course_enrollment_events = ','.join([
        'ga:eventAction==edx.bi.user.course-details.enroll.header',
        'ga:eventAction==edx.bi.user.course-details.enroll.main',
    ])

    featured_program_card_click = ';'.join([
        'ga:eventAction==edx.bi.user.discovery.card.click',
        'ga:eventCategory==program',
        'ga:dimension6==true',
        'ga:pagePath==/',
    ])

    return _featuredCardDrivenEnrollments(date, course_enrollment_events, featured_program_card_click)


def featuredCourseCardDrivenProgramEnrollments(date):
    program_enrollment_events = ','.join([
        'ga:eventAction==edx.bi.user.course-details.enrolled-user.enroll-card',  # New MicroMaster
        'ga:eventAction==edx.bi.user.course-details.enroll.enroll-card',  # New xSeries
        'ga:eventAction==edx.bi.user.course-details.enroll.discovery-card',  # Old MicroMaster
        'ga:eventAction==edx.bi.user.xseries-details.enroll.discovery-card',  # Old xSeries
    ])

    featured_course_card_click = ';'.join([
        'ga:eventAction==edx.bi.user.discovery.card.click',
        'ga:eventCategory==course',
        'ga:dimension6==true',
        'ga:pagePath==/',
    ])

    return _featuredCardDrivenEnrollments(date, program_enrollment_events, featured_course_card_click)


def featuredCourseCardDrivenCourseEnrollments(date):
    course_enrollment_events = ','.join([
        'ga:eventAction==edx.bi.user.course-details.enroll.header',
        'ga:eventAction==edx.bi.user.course-details.enroll.main',
    ])

    featured_course_card_click = ';'.join([
        'ga:eventAction==edx.bi.user.discovery.card.click',
        'ga:eventCategory==course',
        'ga:dimension6==true',
        'ga:pagePath==/',
    ])

    return _featuredCardDrivenEnrollments(date, course_enrollment_events, featured_course_card_click)


def _featuredCardClicks(date, featured_card_click):
    # RETURN total events & unique events
    # GROUPED BY date, label (course/program id), card index
    # FOR anyone who clicked a certain featured card
    # AND whose session sequence was
    #     featured card click EVENTUALLY FOLLOWED BY
    #     a set of enrollment events
    service = get_service()

    data = service.data().ga().get(
        ids='ga:' + '86300562',
        start_date=str(date),
        end_date=str(date),
        max_results=10000,
        metrics='ga:totalEvents,ga:uniqueEvents',
        dimensions='ga:date,ga:eventLabel,ga:dimension5',
        filters=featured_card_click
    ).execute()

    return data.get('rows', [])


def featuredCourseCardClicks(date):
    featured_course_card_click = ';'.join([
        'ga:eventAction==edx.bi.user.discovery.card.click',
        'ga:eventCategory==course',
        'ga:dimension6==true',
        'ga:pagePath==/',
    ])

    return _featuredCardClicks(date, featured_course_card_click)


def featuredProgramCardClicks(date):
    featured_program_card_click = ';'.join([
        'ga:eventAction==edx.bi.user.discovery.card.click',
        'ga:eventCategory==program',
        'ga:dimension6==true',
        'ga:pagePath==/',
    ])

    return _featuredCardClicks(date, featured_program_card_click)


def homePageToSubjectPageData(date):
    # RETURN pageviews & unique pageviews
    # GROUPED BY date & page title
    # FOR anyone who hit the homepage and ended up on a subject page
    service = get_service()
    data = service.data().ga().get(
        ids='ga:' + '86300562',
        start_date=str(date),
        end_date=str(date),
        max_results=10000,
        metrics='ga:pageviews,ga:uniquePageviews',
        dimensions='ga:date,ga:pageTitle',
        filters='ga:previousPagePath==/;ga:pagePath=~^/course/subject/'
    ).execute()

    return data['rows']


def totalHomePageViewsData(date):
    # RETURN pageviews & unique pageviews
    # GROUPED BY date
    # FOR anyone who hit the homepage
    service = get_service()
    data = service.data().ga().get(
        ids='ga:' + '86300562',
        start_date=str(date),
        end_date=str(date),
        max_results=10000,
        metrics='ga:pageviews,ga:uniquePageviews',
        dimensions='ga:date',
        filters='ga:pagePath==/'
    ).execute()

    return data['rows']


def homePageToSubjectPageDataframe(data):
    subject_dataframe = DataFrame(data,columns=['date','page_title','views','uniqueViews'])
    subject_dataframe = subject_dataframe.apply(to_numeric, errors='ignore')
    subject_dataframe.drop('date', axis=1, inplace=True)
    subject_dataframe = subject_dataframe.groupby(['page_title']).sum().sort_values(by='uniqueViews',ascending=0)
    subject_dataframe.reset_index(inplace=True)
    subject_dataframe['subject'] = subject_dataframe['page_title'].apply(lambda title: strip_edx_page_title(title))
    subject_dataframe['totalViews'] = subject_dataframe['uniqueViews'].sum()
    subject_dataframe['Pct'] = (subject_dataframe['uniqueViews'] / subject_dataframe['totalViews'])
    subject_dataframe = subject_dataframe[(subject_dataframe['Pct']>0.0001)]

    return subject_dataframe[['subject','uniqueViews','Pct']]


def totalHomePageViewsValue(data):
    homepage_view_dataframe = DataFrame(data,columns=['date','views','uniqueViews'])
    homepage_view_dataframe = homepage_view_dataframe.apply(to_numeric, errors='ignore')
    return int(homepage_view_dataframe['uniqueViews'].sum())


def mergeProgramAndCourseDataframe(program_df, course_df, total_homepage_views):
    dataframe = concat([program_df, course_df])
    total_clicks = dataframe['uniqueClicks'].sum()
    total_enrolls = dataframe['uniqueEnrolls'].sum()

    dataframe['CTR'] = dataframe['uniqueClicks'] / total_homepage_views
    dataframe['clickShare'] = dataframe['uniqueClicks'] / total_clicks
    dataframe['enrollsPerClick'] = dataframe['uniqueEnrolls'] / total_enrolls

    dataframe = dataframe.sort_values(by='uniqueEnrolls', ascending=0)
    fields = [
        'cardName',
        'position',
        'type',
        'uniqueClicks',
        'CTR',
        'uniqueEnrolls',
        'uniqueProgramEnrolls',
        'uniqueCourseEnrolls',
        'conversionRate',
        'programConversionRate',
        'courseConversionRate',
        'clickShare',
        'clickShareByType',
        'enrollsPerClick',
        'enrollsPerClickByType'
    ]

    return dataframe[fields]


def mergeEnrollmentsAndClicksDataframe(program_program_enrolls, program_course_enrolls,course_program_enrolls, course_course_enrolls, course_clicks, program_clicks):
    program_program_enrolls_df = enrollmentDataframe(program_program_enrolls, 'program', 'Program')
    program_course_enrolls_df = enrollmentDataframe(program_course_enrolls, 'program', 'Course')
    course_program_enrolls_df = enrollmentDataframe(course_program_enrolls, 'course', 'Program')
    course_course_enrolls_df = enrollmentDataframe(course_course_enrolls, 'course', 'Course')

    program_clicks_df = clicksDataframe(program_clicks)
    course_clicks_df = clicksDataframe(course_clicks)

    program_enrolls_df = mergeEnrollmentByTypeDataframe(program_program_enrolls_df, program_course_enrolls_df, program_clicks_df)
    course_enrolls_df = mergeEnrollmentByTypeDataframe(course_program_enrolls_df, course_course_enrolls_df, course_clicks_df)

    return (
        program_enrolls_df,
        course_enrolls_df
    )


def clicksDataframe(clicks_data):
    clicks_dataframe = DataFrame(clicks_data, columns=['date', 'cardName', 'position', 'totalClicks', 'uniqueClicks'])
    clicks_dataframe = clicks_dataframe.apply(to_numeric, errors='ignore')
    clicks_dataframe.drop('date', axis=1, inplace=True)
    clicks_dataframe = clicks_dataframe.groupby(['cardName','position']).sum().sort_values(by='uniqueClicks',ascending=0)
    clicks_dataframe.reset_index(inplace=True)

    return clicks_dataframe


def enrollmentDataframe(enrolls_data, card_type, enroll_type):
    enrolls_dataframe = DataFrame(
        enrolls_data,
        columns=[
            'date',
            'cardName',
            'position',
            'total{type}Enrolls'.format(type=enroll_type),
            'unique{type}Enrolls'.format(type=enroll_type)
        ]
    )

    enrolls_dataframe = enrolls_dataframe.apply(to_numeric, errors='ignore')
    enrolls_dataframe.drop('date', axis=1, inplace=True)
    enrolls_dataframe = enrolls_dataframe.groupby(['cardName','position']).sum().sort_values(by='unique{type}Enrolls'.format(type=enroll_type),ascending=0)
    enrolls_dataframe.reset_index(inplace=True)
    enrolls_dataframe['type'] = card_type

    return enrolls_dataframe


def mergeEnrollmentByTypeDataframe(program_enrolls, course_enrolls, clicks):
    dataframe = merge(
        program_enrolls,
        course_enrolls,
        on=['cardName', 'position', 'type'],
        how='left'
    )

    dataframe = merge(
        dataframe,
        clicks,
        on=['cardName', 'position'],
        how='left'
    )

    total_clicks_by_type = dataframe['uniqueClicks'].sum()

    dataframe['uniqueEnrolls'] = dataframe['uniqueCourseEnrolls'] + dataframe['uniqueProgramEnrolls']
    dataframe['conversionRate'] = dataframe['uniqueEnrolls'] / dataframe['uniqueClicks']
    dataframe['programConversionRate'] = dataframe['uniqueProgramEnrolls'] / dataframe['uniqueClicks']
    dataframe['courseConversionRate'] = dataframe['uniqueCourseEnrolls'] / dataframe['uniqueClicks']
    dataframe['clickShareByType'] = dataframe['uniqueClicks'] / total_clicks_by_type
    dataframe['enrollsPerClickByType'] = dataframe['uniqueEnrolls'] / total_clicks_by_type

    return dataframe


def strip_edx_page_title(page_title):
    return page_title.replace(' | edX', '')


def output_report(filename, total_homepage_views=None, total_course_card_clicks=None, total_program_card_clicks=None, featured_cards=None, homepage_subjects=None):
    writer = ExcelWriter(filename,engine='xlsxwriter')

    # Get access to the workbook
    workbook = writer.book

    # Set the formats needed for the report
    money_fmt = workbook.add_format({'num_format': '$#,##0', 'bold': True})
    percent_fmt = workbook.add_format({'num_format': '0.0%', 'bold': False})
    comma_fmt = workbook.add_format({'num_format': '#,##0', 'bold': False})
    date_fmt = workbook.add_format({'num_format': 'dd/mm/yy'})
    cell_format = workbook.add_format({'bold': True, 'italic': False})
    merge_format = workbook.add_format(
        {
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
        }
    )


    # Create the homepage courses worksheet
    if featured_cards is not None:
        featured_cards.to_excel(writer, index=False, sheet_name='Featured Card Report', startrow=18)
        featured_cards_worksheet = writer.sheets['Featured Card Report']

        # Set column width and formatting
        featured_cards_worksheet.set_column('A:A', 60)
        featured_cards_worksheet.set_column('D:D', 15, comma_fmt)
        featured_cards_worksheet.set_column('E:E', 15, percent_fmt)
        featured_cards_worksheet.set_column('F:H', 15, comma_fmt)
        featured_cards_worksheet.set_column('I:O', 15, percent_fmt)

        # Write headings
        featured_cards_worksheet.write(
            'A1',
            'Homepage Course Enrollments, Data from {start} to {end}'.format(start=start_date, end=end_date),
            cell_format
        )
        featured_cards_worksheet.write('A3', 'Overview', cell_format)
        featured_cards_worksheet.write('A4', 'Total Homepage Views:', cell_format)
        featured_cards_worksheet.write('A6', 'Total feat. Card Clicks on Home Page:', cell_format)
        featured_cards_worksheet.write('A7', '     feat. course clicks', cell_format)
        featured_cards_worksheet.write('A8', '     feat. program clicks', cell_format)
        featured_cards_worksheet.write('A10', 'Total CTR', cell_format)
        featured_cards_worksheet.write('C12', 'card conversion', cell_format)
        featured_cards_worksheet.write('A13', 'Total Enrollments from card clicks:', cell_format)
        featured_cards_worksheet.write('A14', '      enrollment on course about (top+bottom)', cell_format)
        featured_cards_worksheet.write('A15', '      enrolllment on program about', cell_format)
        featured_cards_worksheet.write('A18', 'Top Performing Cards + Conversion', cell_format)

        featured_cards_worksheet.merge_range('F18:H18', 'enrollment events from card click', merge_format)
        featured_cards_worksheet.merge_range('I18:K18', 'conversion from card click', merge_format)
        featured_cards_worksheet.merge_range('L18:M18', 'clickshare vs. other cards', merge_format)
        featured_cards_worksheet.merge_range('N18:O18', 'enrollments per impression', merge_format)

        # Write Overview Data
        featured_cards_worksheet.write('B4', total_homepage_views, comma_fmt)
        featured_cards_worksheet.write('B6', int(featured_cards['uniqueClicks'].sum()), comma_fmt)
        featured_cards_worksheet.write('B7', total_course_card_clicks, comma_fmt)
        featured_cards_worksheet.write('B8', total_program_card_clicks, comma_fmt)
        featured_cards_worksheet.write('B10', float(featured_cards['uniqueClicks'].sum())/total_homepage_views, percent_fmt)
        featured_cards_worksheet.write('B13', int(featured_cards['uniqueEnrolls'].sum()), comma_fmt)
        featured_cards_worksheet.write('B14', int(featured_cards['uniqueCourseEnrolls'].sum()), comma_fmt)
        featured_cards_worksheet.write('B15', int(featured_cards['uniqueProgramEnrolls'].sum()), comma_fmt)
        featured_cards_worksheet.write('C13', float(featured_cards['uniqueEnrolls'].sum())/total_homepage_views, percent_fmt)
        featured_cards_worksheet.write('C14', float(featured_cards['uniqueCourseEnrolls'].sum()) / total_homepage_views, percent_fmt)
        featured_cards_worksheet.write('C15', float(featured_cards['uniqueProgramEnrolls'].sum()) / total_homepage_views, percent_fmt)

    if homepage_subjects is not None:
        homepage_subjects.to_excel(writer, index=False, sheet_name='HomepageSubjects', startrow=2)

        # Get the homepage subject worksheet
        homepage_subject_worksheet = writer.sheets['HomepageSubjects']

        # Set conditional format
        homepage_subject_worksheet.conditional_format('C1:C1000', {'type': '3_color_scale'})

        # Set column width and formatting
        homepage_subject_worksheet.set_column('A:A', 27)
        homepage_subject_worksheet.set_column('B:B', 15, comma_fmt)
        homepage_subject_worksheet.set_column('C:S', 15, percent_fmt)

        # Write heading
        homepage_subject_worksheet.write('A1', 'Top Subject Pages from the Homepage, Data from '+str(start_date)+' to '+str(end_date) , cell_format)

    # Write out the .xlsx file
    writer.save()


def run(start_date, end_date, filepath):
    # get all of the report data
    homepage_to_subject_page_data = homePageToSubjectPageData(start_date)
    total_homepage_views_data = totalHomePageViewsData(start_date)
    program_card_program_enroll_data = featuredProgramCardDrivenProgramEnrollments(start_date)
    program_card_course_enroll_data = featuredProgramCardDrivenCourseEnrollments(start_date)
    course_card_program_enroll_data = featuredCourseCardDrivenProgramEnrollments(start_date)
    course_card_course_enroll_data = featuredCourseCardDrivenCourseEnrollments(start_date)
    course_card_clicks = featuredCourseCardClicks(start_date)
    program_card_clicks = featuredProgramCardClicks(start_date)
    print(start_date)
    delta = end_date - start_date
    for i in range(1, delta.days + 1):
        next_date = start_date + timedelta(days=i)
        homepage_to_subject_page_data += homePageToSubjectPageData(next_date)
        total_homepage_views_data += totalHomePageViewsData(next_date)
        program_card_program_enroll_data += featuredProgramCardDrivenProgramEnrollments(next_date)
        program_card_course_enroll_data += featuredProgramCardDrivenCourseEnrollments(next_date)
        course_card_program_enroll_data += featuredCourseCardDrivenProgramEnrollments(next_date)
        course_card_course_enroll_data += featuredCourseCardDrivenCourseEnrollments(next_date)
        course_card_clicks += featuredCourseCardClicks(next_date)
        program_card_clicks += featuredProgramCardClicks(next_date)
        print(next_date)

    subject_dataframe = homePageToSubjectPageDataframe(homepage_to_subject_page_data)
    total_homepage_views = totalHomePageViewsValue(total_homepage_views_data)
    program_card_df, course_card_df = mergeEnrollmentsAndClicksDataframe(
        program_card_program_enroll_data,
        program_card_course_enroll_data,
        course_card_program_enroll_data,
        course_card_course_enroll_data,
        course_card_clicks,
        program_card_clicks
    )

    total_course_card_clicks = course_card_df['uniqueClicks'].sum()
    total_program_card_clicks = program_card_df['uniqueClicks'].sum()

    featured_card_df = mergeProgramAndCourseDataframe(program_card_df, course_card_df, total_homepage_views)

    # create filename from inputs
    filename = "{filepath}HP Data {start_date} to {end_date}.xlsx".format(
        filepath=filepath,
        start_date=start_date,
        end_date=end_date
    )

    # generate report
    output_report(
        filename,
        total_homepage_views=total_homepage_views,
        total_course_card_clicks=total_course_card_clicks,
        total_program_card_clicks=total_program_card_clicks,
        featured_cards=featured_card_df,
        homepage_subjects=subject_dataframe
    )


def parse_date(date):
    return datetime.strptime(date, '%Y-%m-%d').date()


# parse script arguments
start_date = parse_date(sys.argv[1])
end_date = parse_date(sys.argv[2])
filepath = sys.argv[3]

# Run the report
run(start_date, end_date, filepath)
