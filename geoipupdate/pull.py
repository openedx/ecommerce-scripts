#!/usr/bin/env python3
"""

This script can be used to automatically download geoip maxmind database,
commit, push, and merge them to their respective repos, and then push them to edx-platform.

To use, export an environment variable `GITHUB_ACCESS_TOKEN`. The token requires
GitHub's "repo" scope.

Run the script from the root of this repo.

    python geoipupdate/pull.py git@github.com:edx/edx-platform.git

If you want to use a custom merge method pass the --merge-method option.

    python geoipupdate/pull.py git@github.com:edx/course-discovery.git --merge-method rebase

"""

import sys
import os
sys.path.append(os.path.abspath('transifex'))

from argparse import ArgumentParser
from utils import DEFAULT_MERGE_METHOD, MERGE_METHODS, repo_context
from geoip import download_file

# The name of the branch to use.
BRANCH_NAME = 'geoip2-bot-update-country-database'

# The commit message to use.
MESSAGE = 'geoip2: update maxmind geolite country database'


def pull(clone_url, repo_owner, merge_method=DEFAULT_MERGE_METHOD,
         skip_check_changes=True):
    """Pulls translations for the given repo.

    If applicable, commits them, pushes them to GitHub, opens a PR, waits for
    status checks to pass, then merges the PR and deletes the branch.

    """
    with repo_context(clone_url, repo_owner, BRANCH_NAME, MESSAGE, merge_method=merge_method) as repo:
        current_directory = os.getcwd()
        download_file(current_directory)

        repo.commit_push_and_open_pr(skip_check_changes)

        if repo.pr:
            repo.merge_pr()


def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument(
        'clone_url',
        help='URL to use to clone the repository.'
    )
    parser.add_argument(
        'repo_owner',
        help='This is the user/team that will be pinged when errors occur.'
    )
    parser.add_argument(
        '--merge-method',
        choices=MERGE_METHODS,
        default=DEFAULT_MERGE_METHOD,
        help='Method to use when merging the PR. See https://developer.github.com/v3/pulls/#merge-a-pull-request-merge-button for details.'
    )
    parser.add_argument(
        '--skip_commit',
        action='store_true',
        help='Use this if you do not want to commit changes to repo.'
    )
    parser.add_argument(
        '--skip-check-changes',
        action='store_true',
        default=True,
        help='Skip the check changes step.'
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    pull(
        args.clone_url,
        args.repo_owner,
        merge_method=args.merge_method,
        skip_check_changes=args.skip_check_changes,
    )
