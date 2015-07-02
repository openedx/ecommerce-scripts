#! /usr/bin/env python

""" Verify all completed orders have active enrollments. """
from contextlib import closing
from datetime import timedelta, datetime
import logging
import os
import sys

import MySQLdb
import pandas

logger = logging.getLogger(__name__)


def setup_logging():
    """ Setup logging.

    Add support for console logging, and avoid truncation by pandas.
    """
    msg_format = '%(asctime)s - %(levelname)s - %(message)s'
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(msg_format))
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)

    pandas.set_option('display.max_rows', 500)
    pandas.set_option('display.max_columns', 500)
    pandas.set_option('display.width', 1000)


ecommerce_db = MySQLdb.connect(host=os.environ['ECOMMERCE_DB_HOST'],
                               user=os.environ['ECOMMERCE_DB_USER'],
                               passwd=os.environ['ECOMMERCE_DB_PASSWORD'],
                               db=os.environ['ECOMMERCE_DB_NAME'])

edxapp_db = MySQLdb.connect(host=os.environ['EDXAPP_DB_HOST'],
                            user=os.environ['EDXAPP_DB_USER'],
                            passwd=os.environ['EDXAPP_DB_PASSWORD'],
                            db=os.environ['EDXAPP_DB_NAME'])

# This is the number of minutes to look back when retrieving orders (e.g. all orders in the last 15 minutes).
ORDER_WINDOW_START_TIME = int(os.environ.get('ORDER_WINDOW_START_TIME', 20))


def get_orders(date_placed):
    """ Retrieve all completed orders placed after the given date. """
    sql = """SELECT
    u.username
    , o.number
    , o.date_placed
    , o.total_excl_tax
    , modes.value_text AS 'mode'
    , pav.value_text AS 'course_id'
FROM
    order_order o
    JOIN ecommerce_user u ON (o.user_id = u.id)
    JOIN order_line ol ON (ol.order_id = o.id)
    JOIN catalogue_productattributevalue pav ON (pav.product_id = ol.product_id)
    JOIN catalogue_productattribute pa ON (pa.id = pav.attribute_id AND pa.code = 'course_key')
    JOIN ( SELECT pav2.product_id, pav2.value_text
    FROM catalogue_productattributevalue pav2
    JOIN catalogue_productattribute pa2 ON (pa2.id = pav2.attribute_id AND pa2.code = 'certificate_type')
    ) AS modes ON (modes.product_id = ol.product_id)
    LEFT JOIN refund_refundline rl ON (rl.order_line_id = ol.id)
WHERE
    o.status = 'Complete'
    AND o.date_placed > %s
    AND rl.id IS NULL
ORDER BY
    u.username ASC
    , pav.value_text ASC
    , o.date_placed ASC;
"""
    date_placed = date_placed.strftime('%Y-%m-%d %H:%M:%S')
    orders = pandas.read_sql_query(sql, ecommerce_db, index_col='number', params=(date_placed,),
                                   parse_dates=('date_placed',))
    orders.reset_index(level=0, inplace=True)
    original_order_count = len(orders)

    # Identify upgrades and remove the honor purchase.
    # TODO We will need to do the same for credit.
    grouped = orders.groupby(['username', 'course_id'])
    for key, row_ids in grouped.groups.iteritems():
        username, course_id = key
        if len(row_ids) > 1:
            row_ids.sort()
            honor_order = orders.ix[row_ids[0]]
            verified_order = orders.ix[row_ids[1]]

            logger.info(
                'User [%s] upgraded for course [%s]. Honor order [%s] will be ignored in favor of verified order [%s].',
                username, course_id, honor_order['number'], verified_order['number'])
            orders = orders.drop(row_ids[0])

    logger.info('Dropped [%d] orders.', original_order_count - len(orders))
    return orders


def get_enrollments(usernames, course_ids):
    """ Retrieve all enrollments for the given courses and users. """
    sql = """SELECT
    u.username
    , e.course_id
    , e.mode
    , e.is_active
FROM
    student_courseenrollment e
    JOIN auth_user u ON (u.id = e.user_id)
WHERE
    u.username IN ({usernames})
    AND e.course_id in ({course_ids});
""".format(usernames=','.join('%s' for __ in usernames), course_ids=','.join('%s' for __ in course_ids))

    params = list(usernames) + list(course_ids)
    enrollments = pandas.read_sql_query(sql, edxapp_db, params=params)
    return enrollments


def identify_missing_enrollments(orders, enrollments):
    """ Identify the orders that do not have corresponding enrollments. """
    merged = pandas.merge(orders, enrollments, on=['username', 'course_id', 'mode'], how='left')
    unfulfilled_orders = merged[merged.is_active.isnull()]
    return unfulfilled_orders


def run_audit():
    date_placed = datetime.utcnow() - timedelta(minutes=ORDER_WINDOW_START_TIME)
    orders = get_orders(date_placed)
    usernames = pandas.unique(orders.username.ravel())
    course_ids = pandas.unique(orders.course_id.ravel())
    num_orders = len(orders)
    logger.info('Retrieved [%d] orders, for [%d] users and [%d] courses, from the ecommerce database.',
                num_orders, len(usernames), len(course_ids))

    enrollments = get_enrollments(usernames, course_ids)
    num_enrollments = len(enrollments)
    logger.info('Retrieved [%d] enrollments from the edxapp database.', num_enrollments)

    unfulfilled_orders = identify_missing_enrollments(orders, enrollments)
    if len(unfulfilled_orders) > 0:
        logger.error(u'Identified [%d] unfulfilled order(s):\n%s',
                     len(unfulfilled_orders), unfulfilled_orders.to_string(index=False))
        return False

    logger.info('No unfulfilled orders identified. All is well.')
    return True


if __name__ == "__main__":
    setup_logging()

    logger.info('Audit started...')
    with closing(ecommerce_db):
        with closing(edxapp_db):
            try:
                if not run_audit():
                    # Use a non-zero exit code to indicate an error
                    sys.exit(1)
            finally:
                logger.info('Audit completed.')
