"""
This script is deprecated, but can be used as a reference for MailChimp and SailThru API interaction.
-Brian Fohl, 4/26/2016
"""


import json
import requests
from sailthru.sailthru_client import SailthruClient
from sailthru.sailthru_response import SailthruResponseError
from sailthru.sailthru_error import SailthruClientError

sailthru_api_key = ''
sailthru_api_secret = ''
sailthru_client = SailthruClient(sailthru_api_key, sailthru_api_secret)
mailchimp_list_id = ""
mailchimp_api_key = ""
mailchimp_url = "https://us5.api.mailchimp.com/export/1.0/list?apikey=" + mailchimp_api_key + "&id=" + mailchimp_list_id

max_number_of_users = 0

def add_user_to_sailthru(user):
    data = {"id": user['Email Address']}
    data['name'] = user['Name']
    data['vars'] = user
    print json.dumps(data)

    # try:
    #     response = sailthru_client.api_post("user", data)
    # except SailthruClientError as e:
    #     # Handle exceptions
    #     print ("Exception")
    #     print (e)
    #
    # if response.is_ok():
    #     body = response.get_body()
    #     # handle body which is of type dictionary
    #     print (body)
    # else:
    #     error = response.get_error()
    #     print ("Error: " + error.get_message())
    #     print ("Status Code: " + str(response.get_status_code()))
    #     print ("Error Code: " + str(error.get_error_code()))


# Main code execution
r = requests.post(mailchimp_url, stream=True)
print(r.status_code, r.reason)

headers = []
headers_read = False
users_created = 0

for line in r.iter_lines():
    if max_number_of_users > 0 and users_created == max_number_of_users:
        break
    if line:
        # First line will contain headers / field names, so we'll retain that in an array.
        if not headers_read:
            headers = json.loads(line)
            headers_read = True
        # Each additional line will be a user record, and a dictionary object will be created with the stored headers
        # as keys.
        else:
            json_obj = json.loads(line)
            dictionary = dict(zip(headers, json_obj))

            add_user_to_sailthru(dictionary)
            users_created += 1


