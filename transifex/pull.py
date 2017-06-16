#!/usr/bin/env python3
"""
This script can be used to automatically pull translations from Transifex,
commit, push, and merge them to their respective repos.

To use, export an environment variable `GITHUB_ACCESS_TOKEN`. The token requires
GitHub's "repo" scope.

Run the script from the root of this repo. To use the repo clone URLs stored in
settings.yaml, simply run:

    python transifex/pull.py

If you want to run the script for a specific repo, provide a clone URL as an argument:

    python transifex/pull.py git@github.com:edx/course-discovery.git

If you want to skip the compile messages step, pass the --skip-compilemessages option.

    python transifex/pull.py git@github.com:edx/course-discovery.git --skip-compilemessages
"""
import time
from argparse import ArgumentParser
from os.path import abspath, dirname, join

import yaml
from github import GithubException

import concurrent.futures
from utils.common import Repo, cd, logger

# Combined with exponential backoff, limiting retries to 10 results in
# a total 34 minutes of sleep time. Status checks should almost always
# complete in this period.
MAX_RETRIES = 10


def pull(repo):
    """Pulls translations for the given repo.

    If applicable, commits them, pushes them to GitHub, opens a PR, waits for
    status checks to pass, then merges the PR and deletes the branch.
    """
    pr = None
    logger.info('Pulling translations for [%s].', repo.name)

    try:
        repo.clone()

        with cd(repo):
            repo.branch()
            repo.update_translations()

            if repo.is_changed():
                logger.info('Translations have changed for [%s]. Pushing them to GitHub and opening a PR.', repo.name)
                repo.commit()
                repo.push()
                pr = repo.pr()
            else:
                logger.info('No changes detected for [%s]. Cleaning up.', repo.name)

        if pr:
            if repo.compilemessages_failed:
                # Notify the team that message compilation failed.
                pr.create_issue_comment(
                    '@{owner} failing message compilation prevents this PR from being automatically merged. '
                    'Refer to the Travis build log for more details.'.format(
                        owner=repo.owner
                    )
                )

                # Return immediately, without trying to merge the PR. We don't
                # want to merge PRs without compiled messages.
                return

            retries = 0
            while retries <= MAX_RETRIES:
                try:
                    pr.merge()
                    logger.info('Merged [%s/#%d]. Cleaning up.', repo.name, pr.number)
                    break
                except GithubException as e:
                    # Assumes only one commit is present on the PR.
                    statuses = pr.get_commits()[0].get_statuses()

                    # Check for any failing Travis builds. If any are found, notify the team
                    # and move on.
                    if any('travis' in s.context and s.state == 'failure' for s in statuses):
                        logger.info(
                            'A failing Travis build prevents [%s/#%d] from being merged. Notifying %s.',
                            repo.name, pr.number, repo.owner
                        )

                        pr.create_issue_comment(
                            '@{owner} a failed Travis build prevented this PR from being automatically merged.'.format(
                                owner=repo.owner
                            )
                        )

                        break
                    else:
                        logger.info(
                            'Status checks on [%s/#%d] are pending. This is retry [%d] of [%d].',
                            repo.name, pr.number, retries, MAX_RETRIES
                        )

                        retries += 1

                        if retries <= MAX_RETRIES:
                            # Exponential backoff.
                            time.sleep(2 ** retries)
            else:
                logger.info(
                    'Retry limit hit for [%s/#%d]. Notifying %s.',
                    repo.name, pr.number, repo.owner
                )

                # Retry limit hit. Notify the team and move on.
                pr.create_issue_comment(
                    '@{owner} pending status checks prevented this PR from being automatically merged.'.format(
                        owner=repo.owner
                    )
                )
    finally:
        repo.cleanup(pr)


def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument(
        'clone_url',
        nargs='?',
        help='URL to use to clone the repository. If blank, URLs will be pulled from settings.yaml'
    )
    parser.add_argument(
        '--skip-compilemessages',
        action='store_true',
        help='Skip the message compilation step.'
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()

    if args.clone_url:
        repo = Repo(args.clone_url, skip_compilemessages=args.skip_compilemessages)
        pull(repo)
    else:
        logger.info('No arguments provided. Using settings.yaml.')

        settings_file = join(abspath(dirname(__file__)), 'settings.yaml')
        with open(settings_file) as f:
            settings = yaml.load(f)

        with concurrent.futures.ProcessPoolExecutor() as executor:
            for clone_url in settings['repos']:
                repo = Repo(clone_url, skip_compilemessages=args.skip_compilemessages)
                executor.submit(pull, repo)
