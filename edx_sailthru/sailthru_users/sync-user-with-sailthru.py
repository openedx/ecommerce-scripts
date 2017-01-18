import csv
import subprocess
import sys
import json
import time
from sailthru.sailthru_client import SailthruClient

HOST = "schenedx@tools-edx-gp.edx.org"


def get_data_from_read_replica(usernames):
    users_table = []
    # Ports are handled in ~/.ssh/config since we use OpenSSH
    command = "mysql -u read_only -h prod-edx-replica-rds.edx.org -p\"gwrpRpi28kUYxBksd1Tb1KaLCO2hri\" wwc -e \"select username, email, is_active from auth_user where username in ('{}')\" -s -N".format(
        '\',\''.join(usernames)
    )

    ssh = subprocess.Popen(
        ["ssh", "%s" % HOST, command],
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    result = ssh.stdout.readlines()
    if result == []:
        error = ssh.stderr.readlines()
        print >>sys.stderr, "ERROR: %s" % error
    else:
        for item in result:
            user_row = str.split(item.rstrip(), '\t')
            if len(user_row) == 3:
                users_table.append(
                    {
                        'username': user_row[0],
                        'email': user_row[1],
                        'is_active': int(user_row[2])
                    }
                )
    return users_table


def write_to_file(file, data):
    for item in data:
        filejson = {
            'id': item['email'],
            'vars': {'activated': item['is_active']}
        }
        file.write(json.dumps(filejson))
        file.write('\n')


def upload_to_sailthru(file):
    sailthru_client = SailthruClient('d50d1dac0ae6f50b885a618a7d36d4e0', '844bf4965e85e43da2267b8ac0fb5c1c')
    request_data = {
        'job': 'update',
        'file': file.name
    }
    print 'Upload {} to sailthru'.format(file.name)
    response = sailthru_client.api_post('job', request_data, {'file': 1})

    if response.is_ok():
        job_id = response.get_body().get("job_id")
        print "Update job started on SailThru - JOB ID: " + job_id + " for file " + file.name

        # Keeping checking status until we find out that it's done
        while True:
            print "waiting for update to complete..."
            time.sleep(10)
            response = sailthru_client.api_get('job', {'job_id': job_id})
            if response.get_body().get("status") == "completed":
                return

        else:
            error = response.get_error()
            print "Error: " + error.get_message()
            print "Status Code: " + str(response.get_status_code())
            print "Error Code: " + str(error.get_error_code())


def process():
    username_list = []
    with open('not_activated_edx_users_dynamic.csv', 'rb') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',')
        for row in spamreader:
            if row[2]:
                username_list.append(row[2])
    print 'usernames size: {}'.format(len(username_list))

    print username_list

    batch_size = 500
    offset = 1
    file1 = None
    while offset < len(username_list):
        end_index = min(offset + batch_size, len(username_list) - 1)
        paged = username_list[offset:end_index]
        offset = end_index
        # Connect to the read replica to get the is_active bit
        users = get_data_from_read_replica(paged)
        file1 = open('batch.txt', 'a')
        write_to_file(file1, users)

    upload_to_sailthru(file1)


if __name__ == "__main__":
    process()
