import logging

from edx_rest_api_client.client import EdxRestApiClient


logger = logging.getLogger()


class CatalogApiService:
    """The service to interface with Catalog"""

    def __init__(self, oauth_access_token_url, oauth_key, oauth_secret, api_url_root):
        try:
            self.access_token, expires = EdxRestApiClient.get_oauth_access_token(
                oauth_access_token_url,
                oauth_key,
                oauth_secret, token_type='jwt'
            )
        except Exception:
            logger.exception('No access token acquired through client_credential flow.')
            raise

        logger.info('Retrieved access token.')

        self.api_client = EdxRestApiClient(api_url_root, jwt=self.access_token)
