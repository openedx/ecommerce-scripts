import os

from sailthru.sailthru_client import SailthruClient

sailthru_client = SailthruClient(os.environ['SAILTHRU_API_KEY'], os.environ['SAILTHRU_API_SECRET'])


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

    return {body['keys']}


def add_user_to_sailthru(user):
    data = {"id": user['Email Address']}
    data['name'] = user['Name']
    data['vars'] = user

    response = sailthru_client.api_post("user", data)


    if response.is_ok():
        body = response.get_body()
        # handle body which is of type dictionary
        print (body)
    else:
        error = response.get_error()
        print ("Error: " + error.get_message())
        print ("Status Code: " + str(response.get_status_code()))
        print ("Error Code: " + str(error.get_error_code()))


def main():


if __name__ == "__main__":
    main()
