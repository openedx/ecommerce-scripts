import argparse
import logging

import MySQLdb
import os
import pandas
import sys
from sailthru.sailthru_client import SailthruClient

logger = logging.getLogger(__name__)


def setup_logging():
    logger.setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')


def get_list_of_inactive_users(args):
    edxapp_db = MySQLdb.connect(host=args.mysql_host,
                                user=args.mysql_user,
                                passwd=args.mysql_pass,
                                db=args.db)

    if args.is_active is None:
        active_query = ""
    elif args.is_active:
        active_query = "AND au.is_active=1"
    else:
        active_query = "AND au.is_active=0"

    sql = """SELECT au.email, au.is_active, ar.activation_key
    FROM auth_user au
    INNER JOIN auth_registration ar
    ON au.id=ar.user_id
    """ + active_query

    users_data = pandas.read_sql_query(sql, edxapp_db)

    return users_data


def update_user_on_sailthru(users_data, client):
    logger.info("Starting updating users on sailthru")

    for index, user in users_data.iterrows():
        request_data = {
            "id": user["email"],
            "vars": {
                "activation_key": user["activation_key"]
            },

        }
        response = client.api_post('user', request_data)

        if response.is_ok():
            logger.info("User updated: %s" % user["email"])

        else:
            error = response.get_error()
            logger.error("Error: " + error.get_message())
            logger.error("Status Code: " + str(response.get_status_code()))
            logger.error("Error Code: " + str(error.get_error_code()))


def get_args(argv):
    parser = argparse.ArgumentParser(description='Import activation codes of inactive users from LMS to Sailthru')

    parser.add_argument(
        '--sailthru_key',
        help='Sailthru access key.'
    )

    parser.add_argument(
        '--sailthru_secret',
        help='Sailthru access secret.'
    )

    parser.add_argument(
            '--mysql_host',
            default=os.environ.get('EDXAPP_DB_HOST', ''),
            help='Host address for edx db replica.'
        )

    parser.add_argument(
        '--mysql_user',
        default=os.environ.get('EDXAPP_DB_USER', ''),
        help='Edxapp db user.'
    )

    parser.add_argument(
        '--mysql_pass',
        default=os.environ.get('EDXAPP_DB_PASSWORD', ''),
        help='Password for edx db replica.'
        )

    parser.add_argument(
            '--db',
            default=os.environ.get('EDXAPP_DB_NAME', ''),
            help='DB name.'
    )

    parser.add_argument(
            '--inactive_users_only',
            dest='is_active',
            action="store_false",
            help='Filter only inactive users'
    )

    parser.add_argument(
            '--active_users_only',
            dest='is_active',
            action="store_true",
            help='Filter only active users'
    )
    parser.set_defaults(is_active=None)

    return parser.parse_args()


def main(argv):
    args = get_args(argv)

    user_data = get_list_of_inactive_users(args)

    logger.info("Total users are: %s." %len(user_data))

    sailthru_client = SailthruClient(args.sailthru_key, args.sailthru_secret)
    update_user_on_sailthru(users_data=user_data, client=sailthru_client)

    logger.info("All users are updated!")


if __name__ == "__main__":
    setup_logging()
    logger.info("User update job started.")
    main(sys.argv[1:])
