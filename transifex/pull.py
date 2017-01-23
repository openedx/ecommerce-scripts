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
"""
import concurrent.futures
from contextlib import contextmanager
import logging
from logging.config import dictConfig
import os
from os.path import join, abspath, dirname
import re
import subprocess
import sys
import time
from urllib.parse import urlparse

from github import Github, GithubException
import yaml


# Configure logging.
dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)s %(process)d [%(filename)s:%(lineno)d] - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
    },
})
logger = logging.getLogger()

# Combined with exponential backoff, limiting retries to 10 results in
# a total 34 minutes of sleep time. Status checks should almost always
# complete in this period.
MAX_RETRIES = 10

# Initialize GitHub client. For documentation,
# see http://pygithub.github.io/PyGithub/v1/reference.html.
github_access_token = os.environ['GITHUB_ACCESS_TOKEN']
github = Github(github_access_token)
edx = github.get_organization('edx')


class Repo:
    """Utility representing a Git repo."""
    def __init__(self, clone_url):
        # See https://github.com/blog/1270-easier-builds-and-deployments-using-git-over-https-and-oauth.
        parsed = urlparse(clone_url)
        self.clone_url = '{scheme}://{token}@{netloc}{path}'.format(
            scheme=parsed.scheme,
            token=github_access_token,
            netloc=parsed.netloc,
            path=parsed.path
        )

        match = re.match(r'.*edx/(?P<name>.*).git', self.clone_url)
        self.name = match.group('name')

        self.github_repo = edx.get_repo(self.name)
        self.owner = None
        self.branch_name = 'update-translations'
        self.message = 'Update translations'
        self.is_compiled = True

    def clone(self):
        """Clone the repo."""
        subprocess.run(['git', 'clone', '--depth', '1', self.clone_url], check=True)

        # Assumes the existence of repo metadata YAML, standardized in
        # https://open-edx-proposals.readthedocs.io/en/latest/oep-0002.html.
        with open('{}/openedx.yaml'.format(self.name)) as f:
            repo_metadata = yaml.load(f)
            self.owner = repo_metadata['owner']

    def branch(self):
        """Create and check out a new branch."""
        subprocess.run(['git', 'checkout', '-b', self.branch_name], check=True)

    def update_translations(self):
        """Download and compile messages from Transifex.

        Assumes this repo defines the `pull_translations` Make target and a
        project config file at .tx/config. Running the Transifex client also
        requires specifying Transifex credentials at ~/.transifexrc.

        See http://docs.transifex.com/client/config/.
        """
        subprocess.run(['make', 'pull_translations'], check=True)

        # Messages may fail to compile (e.g., a translator may accidentally translate a
        # variable in a Python format string). If this happens, we want to proceed with
        # the PR process and notify the team that messages failed to compile.
        try:
            # The compilemessages command is a script that (as of Django 1.9) scans the project
            # tree for .po files to compile and calls GNU gettext's msgfmt command on them. It
            # doesn't require DJANGO_SETTINGS_MODULE to be defined when run from the project root,
            # and also doesn't need django.setup() to be run. Because of this, we can get away with
            # django-admin.py instead of manage.py. The latter defines a default value for
            # DJANGO_SETTINGS_MODULE and causes django.setup() to run, which is undesirable here for reasons
            # ranging from Python 2/3 incompatibility errors across projects to forcing the installation
            # of packages which provide installed apps custom to each project.
            subprocess.run(['django-admin.py', 'compilemessages'], check=True)
        except subprocess.CalledProcessError:
            self.is_compiled = False

    def is_changed(self):
        """Determine whether any changes were made."""
        completed_process = subprocess.run(['git', 'status', '--porcelain'], stdout=subprocess.PIPE, check=True)
        return bool(completed_process.stdout)

    def commit(self):
        """Commit changes.

        Adds any untracked files, in case new translations are added.
        """
        subprocess.run(['git', 'add', '-A'], check=True)
        try:
            subprocess.run(['git', 'commit', '-m', self.message], check=True)
        except subprocess.CalledProcessError:
            subprocess.run(
                [
                    'git',
                    '-c', 'user.name="{}"'.format(os.environ['GIT_USER_NAME']),
                    '-c', 'user.email={}'.format(os.environ['GIT_USER_EMAIL']),
                    'commit', '-m', self.message
                ],
                check=True
            )

    def push(self):
        """Push branch to the remote."""
        subprocess.run(['git', 'push', '-u', 'origin', self.branch_name], check=True)

    def pr(self):
        """Create a new PR on GitHub."""
        return self.github_repo.create_pull(
            self.message,
            'This PR was created by a script.',
            'master',
            self.branch_name
        )

    def cleanup(self, pr):
        """Delete the local clone of the repo.

        If applicable, also deletes the merged branch from GitHub.
        """
        if pr and pr.is_merged():
            logger.info('Deleting merged branch %s:%s.', self.name, self.branch_name)
            # Delete branch from remote. See https://developer.github.com/v3/git/refs/#get-a-reference.
            ref = 'heads/{branch}'.format(branch=self.branch_name)
            self.github_repo.get_git_ref(ref).delete()

        # Delete cloned repo.
        subprocess.run(['rm', '-rf', self.name], check=True)


@contextmanager
def cd(repo):
    """Utility for changing into and out of a repo."""
    initial_directory = os.getcwd()
    os.chdir(repo.name)
    
    # Exception handler ensures that we always change back to the
    # initial directory, regardless of how control is returned
    # (e.g., an exception is raised while changed into the new directory).
    try:
        yield
    finally:
        os.chdir(initial_directory)


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
            if not repo.is_compiled:
                # Notify the team that message compilation failed.
                pr.create_issue_comment(
                    '@{owner} failing message compilation prevents this PR from being automatically merged. '
                    'Refer to the Travis build log for more details.'.format(
                        owner=repo.owner
                    )
                )

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


if __name__ == '__main__':
    try:
        clone_url = sys.argv[1]
        repo = Repo(clone_url)
        pull(repo)
    except IndexError:
        logger.info('No arguments provided. Using settings.yaml.')

        settings_file = join(abspath(dirname(__file__)), 'settings.yaml')
        with open(settings_file) as f:
            settings = yaml.load(f)

        with concurrent.futures.ProcessPoolExecutor() as executor:
            for clone_url in settings['repos']:
                repo = Repo(clone_url)
                executor.submit(pull, repo)
