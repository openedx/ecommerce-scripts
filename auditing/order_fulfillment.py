#! /usr/bin/env python

""" Verify all completed orders have active enrollments. """
from contextlib import closing
from datetime import timedelta, datetime
from itertools import groupby
import logging
import os
import sys

import MySQLdb
from MySQLdb.cursors import DictCursor

logger = logging.getLogger(__name__)


def setup_logging():
    """ Setup logging.

    Add support for console logging.
    """
    msg_format = '%(asctime)s - %(levelname)s - %(message)s'
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(msg_format))
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)


ecommerce_db = MySQLdb.connect(host=os.environ['ECOMMERCE_DB_HOST'],
                               user=os.environ['ECOMMERCE_DB_USER'],
                               passwd=os.environ['ECOMMERCE_DB_PASSWORD'],
                               db=os.environ['ECOMMERCE_DB_NAME'])

edxapp_db = MySQLdb.connect(host=os.environ['EDXAPP_DB_HOST'],
                            user=os.environ['EDXAPP_DB_USER'],
                            passwd=os.environ['EDXAPP_DB_PASSWORD'],
                            db=os.environ['EDXAPP_DB_NAME'])

# This is the number of minutes to look back when retrieving orders (e.g. all orders in the last 15 minutes).
ORDER_WINDOW_START_TIME = int(os.environ.get('ORDER_WINDOW_START_TIME', 15))


def get_orders(date_placed):
    """ Retrieve all completed orders placed after the given date. """
    sql = """SELECT
    u.username
    , u.email
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
    with closing(ecommerce_db.cursor(DictCursor)) as cursor:
        cursor.execute(sql, (date_placed,))
        orders = list(cursor.fetchall())

    # Identify upgrades and remove the honor purchase.
    # TODO We will need to do the same for credit.
    for key, grouped_orders in groupby(orders, lambda o: (o['username'], o['course_id'])):
        grouped_orders = list(grouped_orders)
        if len(grouped_orders) > 1:
            modes = set([order['mode'] for order in grouped_orders])
            if modes == {'honor', 'verified'}:
                username, course_id = key
                # The honor order should come before the verified order.
                order = grouped_orders[0]
                logger.info('User [%s] recently upgraded for course [%s]. Honor order [%s] will be ignored.', username,
                            course_id, order['number'])
                orders.remove(order)

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

    with closing(edxapp_db.cursor(DictCursor)) as cursor:
        args = list(usernames) + list(course_ids)
        cursor.execute(sql, args)
        return cursor.fetchall()


def identify_missing_enrollments(orders, enrollments):
    """ Identify the orders that do not have corresponding enrollments. """
    enrollments = list(enrollments)
    unfulfilled_orders = []
    for order in orders:
        fulfilled = False
        for enrollment in enrollments:
            if enrollment['username'] == order['username'] and enrollment['course_id'] == order['course_id'] and \
                            enrollment['mode'] == order['mode']:
                fulfilled = True
                enrollments.remove(enrollment)
                break

        if not fulfilled:
            unfulfilled_orders.append(order)

    return unfulfilled_orders


def run_audit():
    date_placed = datetime.utcnow() - timedelta(minutes=ORDER_WINDOW_START_TIME)
    orders = get_orders(date_placed)
    usernames = set([order['username'] for order in orders])
    course_ids = set([order['course_id'] for order in orders])
    num_orders = len(orders)
    logger.info('Retrieved [%d] orders, for [%d] users and [%d] courses, from the ecommerce database.', num_orders,
                len(usernames), len(course_ids))

    enrollments = get_enrollments(usernames, course_ids)
    num_enrollments = len(enrollments)
    logger.info('Retrieved [%d] enrollments from the edxapp database.', num_enrollments)

    unfulfilled_orders = identify_missing_enrollments(orders, enrollments)
    if unfulfilled_orders:
        logger.error(u'Identified [%d] unfulfilled order(s):\n%s', len(unfulfilled_orders),
                     '\n'.join(['\t' + unicode(order) for order in unfulfilled_orders]))
        return False

    logger.info('No unfulfilled orders identified. All is well.')
    return True


if __name__ == "__main__":
    setup_logging()

    with closing(ecommerce_db):
        with closing(edxapp_db):
            if not run_audit():
                # Use a non-zero exit code to indicate an error
                sys.exit(1)
