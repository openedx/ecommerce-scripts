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
from argparse import ArgumentParser
from os.path import abspath, dirname, join

import yaml

import concurrent.futures
from utils.common import Repo, cd, logger


def pull(repo, skip_compilemessages=False):
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
            repo.pull_translations()

            if skip_compilemessages:
                logger.info('Skipping compilemessages.')
            else:
                compilemessages_succeeded = repo.compilemessages()

            pr = repo.commit_push_and_open_pr()

        if pr:
            if not (skip_compilemessages or compilemessages_succeeded):
                # Notify the team that message compilation failed.
                pr.create_issue_comment(
                    '@{owner} failing message compilation prevents this PR from being automatically merged. '
                    'Refer to the build log for more details.'.format(
                        owner=repo.owner
                    )
                )

                # Return immediately, without trying to merge the PR. We don't
                # want to merge PRs without compiled messages.
                return

            repo.merge_pr(pr)

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
        repo = Repo(args.clone_url)
        pull(repo, skip_compilemessages=args.skip_compilemessages)
    else:
        logger.info('No arguments provided. Using settings.yaml.')

        settings_file = join(abspath(dirname(__file__)), 'settings.yaml')
        with open(settings_file) as f:
            settings = yaml.load(f)

        with concurrent.futures.ProcessPoolExecutor() as executor:
            for clone_url in settings['repos']:
                repo = Repo(clone_url)
                executor.submit(pull, repo, skip_compilemessages=args.skip_compilemessages)
