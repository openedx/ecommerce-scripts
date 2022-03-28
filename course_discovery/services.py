import json
import logging

import requests

logger = logging.getLogger()


class CatalogApiService:
    """The service to interface with Catalog"""

    def __init__(self, oauth_access_token_url, oauth_key, oauth_secret, api_url_root):
        self.oauth_key = oauth_key
        self.oauth_secret = oauth_secret
        self.api_url_root = api_url_root
        try:
            response = requests.post(
                oauth_access_token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': oauth_key,
                    'client_secret': oauth_secret,
                    'token_type': 'jwt',
                },
                headers={
                    'User-Agent': 'ecommerce-scripts',
                },
                timeout=(3.1, 5)
            )
            data = response.json()
            self.access_token = data['access_token']
        except (KeyError, json.decoder.JSONDecodeError) as json_error:
            logger.exception('Failed to get access token from response.')
            raise requests.RequestException(response=response) from json_error
        except Exception:
            logger.exception('No access token acquired through client_credential flow.')
            raise

        logger.info('Retrieved access token.')

    def update_course_run(self, key, data):
        headers = {'Authorization': "JWT {}".format(self.access_token)}
        requests.patch(
            f'{self.api_url_root}course_runs/{key}/',
            json=data,
            headers=headers
        )
