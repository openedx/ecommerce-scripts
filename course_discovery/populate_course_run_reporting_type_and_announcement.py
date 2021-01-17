import argparse
import csv
import datetime
import json
import logging
import os

from dateutil.parser import parse

from services import CatalogApiService

def process_line(line):
    announcement = line.get('announcement')
    data = {
        'reporting_type': line['reporting_type']
    }
    if announcement:
        # Convert 2/1/2016 to 2016-02-01T00:00:00+00:00
        announcement = parse(announcement).isoformat()
        data['announcement'] = announcement
    return line['course_run_key'], data

def update_course_run(key, data, catalog_api_service):
    course_runs_endpoint = catalog_api_service.api_client.course_runs(key)
    try:
        response = course_runs_endpoint.patch(data=data)
        logging.info(f'{key} update succeeded')
    except:
        logging.exception('Failed to update course run [%s]', key)

def main():
    parser = argparse.ArgumentParser(description='Populates reporting type and announcment on course runs')
    parser.add_argument('--filename', help='Name of file with data on course run types and announcment dates.')
    parser.add_argument(
        '--oauth_access_token_url',
        default=os.environ.get('CATALOG_OAUTH_ACCESS_TOKEN_URL', 'https://api.edx.org/oauth2/v1/access_token'),
        help='OAuth access token endpoint URL.'
    )
    parser.add_argument(
        '--oauth_key',
        default=os.environ.get('CATALOG_OAUTH_KEY', None),
        help='OAuth client key.'
    )
    parser.add_argument(
        '--oauth_secret',
        default=os.environ.get('CATALOG_OAUTH_SECRET', None),
        help='OAuth2 secret token.'
    )
    parser.add_argument(
        '--catalog_api_url',
        default=os.environ.get('CATALOG_API_URL', 'https://prod-edx-discovery.edx.org/api/v1/'),
        help='Catalog API URL.'
    )


    args = parser.parse_args()

    catalog_api_service = CatalogApiService(
        args.oauth_access_token_url,
        args.oauth_key,
        args.oauth_secret,
        args.catalog_api_url
    )

    with open(args.filename) as f:
        reader = csv.DictReader(f)
        for line in reader:
            key, data = process_line(line)
            update_course_run(key, data, catalog_api_service)


if __name__ == "__main__":
    main()
