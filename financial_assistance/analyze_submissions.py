"""
Analyze financial aid submissions.
"""
import codecs
import json

requests = json.load(codecs.open('cleaned.json', 'r', 'utf-8'))
total = len(requests)
print('{:d} total submissions'.format(total))

# Identify submissions where profile country does not match IP country.
mismatched_country = [request for request in requests if
    request.get('country_iso_code') != request.get('client_ip_iso_code')]
num_mismatched = len(mismatched_country)

print('{:d} ({:.1f}%) submissions have mismatched profile country and IP country.'.format(num_mismatched,
    100.0 * num_mismatched / total))

# Household income
incomes = [request.get('annual_household_income', 0) or 0 for request in requests]
avg_income = sum(incomes) / float(len(incomes))
max_income = max(incomes)
min_income = min(incomes)

print('Minimum annual household income: ${:.2f}'.format(min_income))
print('Average annual household income: ${:.2f}.'.format(avg_income))
print('Maximum annual household income: ${:.2f}'.format(max_income))
