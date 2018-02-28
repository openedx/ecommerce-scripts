#!/usr/bin/env python3
"""
This script can be used to automatically pull translations from Transifex,
commit, push, and merge them to their respective repos.

To use, export an environment variable `GITHUB_ACCESS_TOKEN`. The token requires
GitHub's "repo" scope.

Run the script from the root of this repo.

    python transifex/pull.py git@github.com:edx/course-discovery.git

If you want to use a custom merge method pass the --merge-method option.

    python transifex/pull.py git@github.com:edx/course-discovery.git --merge-method rebase

If you want to skip the compile messages step, pass the --skip-compilemessages option.

    python transifex/pull.py git@github.com:edx/course-discovery.git --skip-compilemessages
"""
from argparse import ArgumentParser

from utils import DEFAULT_MERGE_METHOD, MERGE_METHODS, logger, repo_context


# The name of the branch to use.
BRANCH_NAME = 'transifex-bot-update-translations'

# The commit message to use.
MESSAGE = 'Update translations'


def pull(clone_url, repo_owner, merge_method=DEFAULT_MERGE_METHOD, skip_compilemessages=False):
    """Pulls translations for the given repo.

    If applicable, commits them, pushes them to GitHub, opens a PR, waits for
    status checks to pass, then merges the PR and deletes the branch.
    """
    with repo_context(clone_url, repo_owner, BRANCH_NAME, MESSAGE, merge_method=merge_method) as repo:
        logger.info('Pulling translations for [%s].', repo.name)

        repo.pull_translations()

        if skip_compilemessages:
            logger.info('Skipping compilemessages.')
        else:
            compilemessages_succeeded = repo.compilemessages()

        repo.commit_push_and_open_pr()

        if repo.pr:
            if not (skip_compilemessages or compilemessages_succeeded):

                # Notify the team that message compilation failed.
                repo.pr.create_issue_comment(
                    '@{owner} failing message compilation prevents this PR from being automatically merged. '
                    'Refer to the build log for more details.'.format(
                        owner=repo.owner
                    )
                )

                # Fail job immediately, without trying to merge the PR. We don't
                # want to merge PRs without compiled messages.
                raise RuntimeError('Failed to compile messages.')

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
        '--skip-compilemessages',
        action='store_true',
        help='Skip the message compilation step.'
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    pull(
        args.clone_url,
        args.repo_owner,
        merge_method=args.merge_method,
        skip_compilemessages=args.skip_compilemessages
    )
