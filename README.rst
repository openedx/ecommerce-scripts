Part of `edX code`__.

__ http://code.edx.org/

Miscellaneous edX Utility Scripts
=================================

This package contains scripts useful for managing an edX environment.  Included are the following
The script are coded to run in the Python 2.7 environment

Sailthru Content
----------------

A script intended to be run periodically (e.g. nightly) which uses the Course Discovery API to populate/update
the Sailthru content library.  Useful when Sailthru is used for email marketing. The script invocation syntax is
as follows:

 usage: ./sailthru_content/sync_library.py [-h] [--access_token ACCESS_TOKEN]
                           [--oauth_host OAUTH_HOST] [--oauth_key OAUTH_KEY]
                           [--oauth_secret OAUTH_SECRET]
                           [--sailthru_key SAILTHRU_KEY]
                           [--sailthru_secret SAILTHRU_SECRET]
                           [--content_api_url CONTENT_API_URL]
                           [--lms_url LMS_URL]
                           [--email_report EMAIL_REPORT]
                           [--email_report CHOICE[courses, programs]]
                           {list, preview, upload, clear}

The 'clear' command deletes all the entries currently in the Sailthru content library.  It should generally only be
used during testing before deployment.  The 'list' command displays, in JSON, up to 1000 entries currently in the
Sailthru content library.  The 'preview' command reads the data using the Course Discovery API and translate them into
the Sailthru content library item format appropriately, then print them out to the screen.  The 'upload' command sends the updates to Sailthru as a batch job.  The result is sent as a brief report to the address specified in --email_report.  

The following options are available:

+--------------------------------+----------------------------------------------------------------------------------+
| Switch                         | Purpose                                                                          |
+================================+==================================================================================+
| --access_token                 | An access token for the Course Discovery API                                     |
+--------------------------------+----------------------------------------------------------------------------------+
| --oauth_host                   | The host used to obtain Course Discovery access token                            |
+--------------------------------+----------------------------------------------------------------------------------+
| --oauth_key                    | Key used to obtain Course Discovery access token                                 |
+--------------------------------+----------------------------------------------------------------------------------+
| --oauth_secret                 | Secret used to obtain Course Discovery access token                              |
+--------------------------------+----------------------------------------------------------------------------------+
| --sailthru_key                 | Access key for Sailthru api                                                      |
+--------------------------------+----------------------------------------------------------------------------------+
| --sailthru_secret              | Access secret for Sailthru api                                                   |
+--------------------------------+----------------------------------------------------------------------------------+
| --content_api_url              | Url of Course Discovery API                                                      |
+--------------------------------+----------------------------------------------------------------------------------+
| --lms_url                      | Url of LMS (default http://courses.edx.org)                                      |
+--------------------------------+----------------------------------------------------------------------------------+
| --email_report                 | Email address to sent batch report to                                            |
+--------------------------------+----------------------------------------------------------------------------------+
| --type                         | The data type to synch with Sailthru. Choices: 'all', 'courses', 'programs'      |
+--------------------------------+----------------------------------------------------------------------------------+

To get access to the Course Discovery API, you need either an existing access token, or you can specify the
oauth_host, oauth_key and oauth_secret.

./sailthru_content/sync_library.py --oauth_key=<api key> --oauth_secret=<api secret>
   --oauth_host=https://api.edx.org/oauth2/v1
   --sailthru_key=<sailthru key> --sailthru_secret=<sailthru secret>
   --content_api_url=https://prod-edx-discovery.edx.org/api/v1/
   --lms_url=https://courses.edx.org
   --fixups=fixups.csv
   --email_report=somebody@edx.org
   --type=all upload


License
-------

The code in this repository is licensed under AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.


