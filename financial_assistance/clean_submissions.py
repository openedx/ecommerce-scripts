"""
Clean financial aid submission data.
"""

from __future__ import unicode_literals

import codecs
import json
import re

import pycountry
from geoip import geolite2

# Read requests file created by get_submissions.py
requests = json.load(codecs.open('requests.json', 'r', 'utf-8'))


# Remove test submissions
def is_test_submission(request):
    return request['username'] in ('financial-assistance', 'shelbystack2', 'Davedean',
    'pfogg', 'zrockwell', 'bd3rusha', 'Aswan',)


cleaned_requests = []
for request in requests:
    # Remove test submissions
    if is_test_submission(request):
        continue

    # Clean income field
    trim = re.compile(r'[^\d.]+')
    income = trim.sub('', request['annual_household_income'])
    income = int(income.split('.')[0] or 0)
    request['annual_household_income'] = income

    # Remove outliers
    if income > 100000:
        continue

    # Get GeoIP info
    match = geolite2.lookup(request['client_ip'])

    if match:
        request['client_ip_iso_code'] = match.country

    # Convert profile country to country code
    country = request['country'].strip()

    if country in ('Vietnam', 'Vi\xeat Nam'):
        country = 'Viet Nam'
    elif country == 'Brasil':
        country = 'Brazil'
    elif country == 'Russia':
        country = 'Russian Federation'
    elif country == 'Macedonia':
        country = 'Macedonia, Republic of'

    if country:
        try:
            country = pycountry.countries.get(name=country)
        except KeyError:
            country = pycountry.countries.get(official_name=country)

        request['country_iso_code'] = country.alpha2

    cleaned_requests.append(request)

# Write to new file
json.dump(cleaned_requests, codecs.open('cleaned.json', 'w', 'utf-8'), indent=2)
