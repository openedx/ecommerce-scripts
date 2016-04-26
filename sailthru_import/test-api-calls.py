"""
This script is deprecated, but can be used as a reference for SailThru API interaction.
-Brian Fohl, 4/26/2016
"""

from sailthru.sailthru_client import SailthruClient
from sailthru.sailthru_response import SailthruResponseError
from sailthru.sailthru_error import SailthruClientError

api_key = ''
api_secret = ''
sailthru_client = SailthruClient(api_key, api_secret)

email_id = "bfohl@edx.org"
email_id_fake = "fake@edx.org"


def get_user(email):
    try:
        user_response = sailthru_client.api_get("user", {"id": email})

        if user_response.is_ok():
            body = user_response.get_body()
            # handle body which is of type dictionary
            print (body)

            if body['keys']['sid'] != '':
                print ("User exists!")

        else:
            error = user_response.get_error()
            print ("Error: " + error.get_message())
            print ("Status Code: " + str(user_response.get_status_code()))
            print ("Error Code: " + str(error.get_error_code()))
    except SailthruClientError as e:
        # Handle exceptions
        print ("Exception")
        print (e)

    return {body['keys']}






try:
    user = get_user(email_id)

    # response = sailthru_client.api_get("user", {"id": email_id_fake})
    #
    # if response.is_ok():
    #     body = response.get_body()
    #     # handle body which is of type dictionary
    #     print (body)
    #
    #     if body['keys']['sid'] != '':
    #         print ("User exists!")
    #
    # else:
    #     error = response.get_error()
    #     print ("Error: " + error.get_message())
    #     print ("Status Code: " + str(response.get_status_code()))
    #     print ("Error Code: " + str(error.get_error_code()))



except SailthruClientError as e:
    # Handle exceptions
    print ("Exception")
    print (e)