""" AWS Lambda script. Creates a Zendesk ticket when a user creates a dispute at PayPal. """
import json
import logging

import paypalrestsdk
from paypalrestsdk import WebhookEvent

log = logging.getLogger()
log.setLevel(logging.INFO)


def create_zendesk_ticket(event_resource):
    requester_email = event_resource.buyer_email
    dispute_id = event_resource.dispute_id
    link = 'https://www.paypal.com/us/cgi-bin/webscr?cmd=_unauth-view-details&cid={dispute_id}'.format(
        dispute_id=dispute_id)
    body = 'The requester has initiated opened a dispute at PayPal. ' \
           'Please visit {link} to get more information, and respond to this dispute.'.format(link=link)
    subject = '[PayPal] Dispute created'
    tags = ['paypal']
    log.info(requester_email)
    log.info(dispute_id)

    # TODO Create a Zendesk ticket


def verify_signature(event, body):
    """ Verify the signature of the POST body is valid. """

    transmission_id = event['paypal_transmission_id']
    timestamp = event['paypal_transmission_time']
    webhook_id = event['paypal_webhook_id']
    cert_url = event['paypal_cert_url']
    actual_signature = event['paypal_transmission_sig']
    auth_algo = event['paypal_auth_algo']

    if not WebhookEvent.verify(transmission_id, timestamp, webhook_id, body, cert_url, actual_signature, auth_algo):
        raise ValueError('Signature is not valid!')


def handler(event, context):
    """
    Process the dispute event from PayPal.

    Args:
     event (dict)
     context (LambdaContext)
    """
    log.info(event)

    paypalrestsdk.configure({
        'mode': event['paypal_credentials']['mode'],
        'client_id': event['paypal_credentials']['client_id'],
        'client_secret': event['paypal_credentials']['client_secret']
    })

    body = json.loads(event['body'])
    verify_signature(event, body)

    webhook_event = WebhookEvent(body)
    event_resource = webhook_event.get_resource()

    create_zendesk_ticket(event_resource)
