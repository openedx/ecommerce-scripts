Part of `edX code`__.

__ http://code.edx.org/

Miscellaneous edX Utility Scripts
=================================

This package contains scripts useful for managing an edX environment.  Included are the following

Sailthru Content
----------------

A script intended to be run periodically (e.g. nightly) which uses the Course Discovery API to populate/update
the Sailthru content library.  Useful when Sailthru is used for email marketing. The script invocation syntax is
as follows:

 usage: sailthru_content.py [-h] [--access_token ACCESS_TOKEN]
                           [--oauth_host OAUTH_HOST] [--oauth_key OAUTH_KEY]
                           [--oauth_secret OAUTH_SECRET]
                           [--sailthru_key SAILTHRU_KEY]
                           [--sailthru_secret SAILTHRU_SECRET]
                           [--content_api_url CONTENT_API_URL]
                           [--lms_url LMS_URL]
                           {list,load,clear}

The 'clear' command deletes all the entries currently in the Sailthru content library.  It should generally only be
used during testing before deployment.  The 'list' command displays, in JSON, up to 1000 entries currently in the
Sailthru content library.  The 'load' command reads the course list using the Course Discovery API and adds/updates
the Sailthru content library appropriately.

The following switches are available:

+--------------------------------+-------------------------------------------------------+
| Switch                         | Purpose                                               |
+================================+=======================================================+
| --access_token                 | An access token for the Course Discovery API          |
+--------------------------------+-------------------------------------------------------+
| --oauth_host                   | The host used to obtain Course Discover access token  |
+--------------------------------+-------------------------------------------------------+
| --oauth_key                    | The key used to obtain Course Discover access token   |
+--------------------------------+-------------------------------------------------------+
| --oauth_secret                 | The secret used to obtain Course Discover access token|
+--------------------------------+-------------------------------------------------------+
| --sailthru_key                 | Access key for Sailthru api                           |
+--------------------------------+-------------------------------------------------------+
| --sailthru_secret              | Access secret for Sailthru api                        |
+--------------------------------+-------------------------------------------------------+
| --content_api_url              | Url of Course Discovery API                           |
+--------------------------------+-------------------------------------------------------+
| --lms_url                      | Url of LMS (default http://courses.edx.org            |
+--------------------------------+-------------------------------------------------------+

To get access to the Course Discovery API, you need either an existing access token, or you can specify the
oauth_host, oauth_key and oauth_secret.


License
-------

The code in this repository is licensed under AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.


