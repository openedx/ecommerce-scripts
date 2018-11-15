import datetime
import logging
import os
import re
import subprocess
import time
from contextlib import contextmanager
from logging.config import dictConfig
from urllib.parse import urlparse

import github

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


@contextmanager
def repo_context(*args, **kwargs):
    """Utility for cloning a repo, cd'ing to it, creating a working branch, doing some work, and then cleaning
       everything up.
    """
    repo = Repo(*args, **kwargs)
    try:
        repo.clone()
        with cd(repo):
            repo.branch()
            yield repo
    finally:
        # Make sure that we always cleanup the local workspace and any remote branches that were created,
        # even on error, so that we can reliably re-run the script.
        repo.cleanup()


# Merge methods supported by the Github API. https://developer.github.com/v3/pulls/#merge-a-pull-request-merge-button
NORMAL_MERGE = 'merge'
SQUASH_MERGE = 'squash'
REBASE_MERGE = 'rebase'
MERGE_METHODS = {NORMAL_MERGE, SQUASH_MERGE, REBASE_MERGE}
DEFAULT_MERGE_METHOD = REBASE_MERGE  # Default to rebase merge, since that's what most edx repositories require.


GithubPullRequest = github.PullRequest.PullRequest
class ExtendedPullRequest(GithubPullRequest):
    def merge(self, commit_message=github.GithubObject.NotSet, merge_method=None):
        """
        Reimplemented from https://github.com/PyGithub/PyGithub/blob/v1.29/github/PullRequest.py#L501
        to enable support for the merge_method option (https://developer.github.com/v3/pulls/#merge-a-pull-request-merge-button).

        All of this code was copied exactly from the original version, except for the block between the
        ## Start custom code ## and ## End custom code ## comments.
        """
        assert commit_message is github.GithubObject.NotSet or isinstance(commit_message, str), commit_message
        post_parameters = dict()
        if commit_message is not github.GithubObject.NotSet:
            post_parameters["commit_message"] = commit_message

        ## Start custom code ##
        if merge_method:
            if merge_method not in MERGE_METHODS:
                raise RuntimeError("`{}` is not a supported merge method".format(merge_method))
            post_parameters["merge_method"] = merge_method
        ## End custom code ##

        headers, data = self._requester.requestJsonAndCheck(
            "PUT",
            self.url + "/merge",
            input=post_parameters
        )
        return github.PullRequestMergeStatus.PullRequestMergeStatus(self._requester, headers, data, completed=True)
github.PullRequest.PullRequest = ExtendedPullRequest


# Initialize GitHub client. For documentation,
# see http://pygithub.github.io/PyGithub/v1/reference.html.
github_access_token = os.environ['GITHUB_ACCESS_TOKEN']
edx = github.Github(github_access_token).get_organization('edx')


class Repo:
    # Make 18 attempts to merge the PR (the original attempt plus 17 retries), sleeping for 5 minutes between each
    # attempt. This should result in a total 90 minutes of sleep time. Status checks should almost always
    # complete in this period.
    MAX_MERGE_RETRIES = 17

    """Utility representing a Git repo."""
    def __init__(self, clone_url, repo_owner, branch_name, message, merge_method=DEFAULT_MERGE_METHOD):
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
        self.owner = repo_owner
        self.branch_name = branch_name + str(datetime.date.today())
        self.message = message
        self.pr = None
        self.merge_method = merge_method

    def clone(self):
        """Clone the repo."""
        subprocess.run(['git', 'clone', '--depth', '1', self.clone_url], check=True)

    def branch(self):
        """Create and check out a new branch."""
        subprocess.run(['git', 'checkout', '-b', self.branch_name], check=True)

    def pull_translations(self):
        """Download translation messages from Transifex.

        Assumes this repo defines the `pull_translations` Make target and a
        project config file at .tx/config. Running the Transifex client also
        requires specifying Transifex credentials at ~/.transifexrc.

        See http://docs.transifex.com/client/config/.
        """
        subprocess.run(['make', 'pull_translations'], check=True)

    def compilemessages(self):
        """Run the django-admin compilemessages command and return a bool indicating whether or not it succeeded. """
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
            return True
        except subprocess.CalledProcessError:
            return False

    def extract_translations(self):
        """Extract translation strings from the source code files in this repo.
           Assumes this repo defines the `extract_translations` Make target.
        """
        subprocess.run(['make', 'extract_translations'], check=True)

    def push_translations(self):
        """Push translation strings to Transifex.

        Assumes this repo defines the `push_translations` Make target and a
        project config file at .tx/config. Running the Transifex client also
        requires specifying Transifex credentials at ~/.transifexrc.

        See http://docs.transifex.com/client/config/.
        """
        logger.info('Pushing translations to Transifex for [%s].', self.name)
        subprocess.run(['make', 'push_translations'], check=True)

    def commit_push_and_open_pr(self):
        """Convenience method that will detect changes that have been made to the repo, commit them, push them
           to Github, and open a PR.
        """
        if self.is_changed():
            logger.info('Changes detected for [%s]. Pushing them to GitHub and opening a PR.', self.name)
            self.commit()
            self.push()
            self.open_pr()
        else:
            logger.info('No changes detected for [%s].', self.name)

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

    def open_pr(self):
        """Create a new PR on GitHub."""
        if self.pr:
            raise RuntimeError(
                'A pull request has already been opened. [{repo}/{pr}]'.format(
                    repo=self.name,
                    pr=self.pr.number
                )
            )

        self.pr = self.github_repo.create_pull(
            self.message,
            'This PR was created by a script.',
            'master',
            self.branch_name
        )

    def merge_pr(self):
        if not self.pr:
            raise RuntimeError(
                'A pull request has not been opened for {repo}:{branch}.'.format(
                    repo=self.name,
                    branch=self.branch_name
                )
            )

        if self.pr.is_merged():
            raise RuntimeError(
                'The pull request [{repo}/{pr}] has already been merged.'.format(
                    repo=self.name,
                    pr=self.pr.number
                )
            )

        retries = 0
        while retries <= self.MAX_MERGE_RETRIES:
            # Assumes only one commit is present on the PR.
            time.sleep(60 * 5)
            state = self._get_tests_combined_status()

            if state == 'failure':
                logger.error(
                    'A failing Travis build prevents [%s/#%d] from being merged. Notifying %s.',
                    self.name, self.pr.number, self.owner
                )

                self.pr.create_issue_comment(
                    '@{owner} a failed Travis build prevented this PR from being automatically merged.'.format(
                        owner=self.owner
                    )
                )
                raise RuntimeError('A failed Travis build prevented this PR from being automatically merged.')
            elif state == 'success':
                try:
                    self.pr.merge(merge_method=self.merge_method)
                    logger.info('Merged [%s/#%d].', self.name, self.pr.number)
                    return True
                except github.GithubException as e:
                    logger.error(
                        'Failed to merge [%s/#%d], because of the exception [%s]',
                        self.name, self.pr.number, e,
                    )
                    raise RuntimeError('Failed to merge.')
            else:
                retries += 1
                if retries <= self.MAX_MERGE_RETRIES:
                    logger.info(
                        'Status checks on [%s/#%d] are pending. This is retry [%d] of [%d].',
                        self.name, self.pr.number, retries, self.MAX_MERGE_RETRIES
                    )


        logger.info('Retry limit hit for [%s/#%d]. Notifying %s.', self.name, self.pr.number, self.owner)

        # Retry limit hit. Notify the team and move on.
        self.pr.create_issue_comment(
            '@{owner} pending status checks prevented this PR from being automatically merged.'.format(owner=self.owner)
        )
        raise RuntimeError('Pending status checks prevented this PR from being automatically merged')

    def _get_tests_combined_status(self):
        """ Returns combined status of pr tests """
        commit = self.pr.get_commits()[0]
        combined_statuses = commit.get_combined_status()
        if combined_statuses.total_count > 0:
            return combined_statuses.state

        # Remove this code once pyGithub supports github checks api
        requester = getattr(commit, '_requester')
        __, response = requester.requestJsonAndCheck(
            "GET",
            commit.url + "/check-runs",
            headers={'Accept': 'application/vnd.github.antiope-preview+json'}
        )
        conclusions = []
        for check_run in response['check_runs']:
            conclusion = check_run['conclusion']
            # consider all statuses failure other than success.
            if conclusion and conclusion != 'success':
                return 'failure'
            elif conclusion and conclusion == 'success':
                conclusions.append('success')
        if len(conclusions) == len(response['check_runs']):
            return 'success'
        else:
            return 'pending'

    def cleanup(self):
        """Delete the local clone of the repo.

        If applicable, also deletes the merged branch from GitHub.
        """
        if self.pr:
            logger.info('Deleting branch %s:%s.', self.name, self.branch_name)
            # Delete branch from remote. See https://developer.github.com/v3/git/refs/#get-a-reference.
            ref = 'heads/{branch}'.format(branch=self.branch_name)
            self.github_repo.get_git_ref(ref).delete()

        # Delete cloned repo.
        subprocess.run(['rm', '-rf', self.name], check=True)
