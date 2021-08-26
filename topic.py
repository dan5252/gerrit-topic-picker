#!/usr/bin/python3

#
# Copyright (c) 2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import argparse
import json
import os
import pprint
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET

import requests

SUCCESS = 0
FAILURE = 1

# Cache the repo manifest file information
REPO_MANIFEST = {}


def responseCorrection(content):
    return content[5:]


def handleList(args):
    pass


def addGerritQuery(query_string, field_name, target_values):
    """ Add a query for a specific field.
    """
    if not type(target_values) is list:
        target_values = [target_values]

    if len(target_values) == 0:
        return query_string
    elif len(target_values) == 1:
        return '{} {}:"{}"'.format(query_string, field_name, target_values[0])
    else:
        assemble = '{} ({}:"{}"'.format(query_string, field_name, target_values[0])
        for val in target_values[1:]:
            assemble = '{} OR {}:"{}"'.format(assemble, field_name, val)
        assemble = assemble + ')'
        return assemble


def queryChanges(args):
    query = 'changes/'
    url_query = urllib.parse.urljoin(args.gerrit, query)

    print('Query {}'.format(url_query))

    # GET /changes/?q=topic:"my-topic"&o=CURRENT_REVISION&o=DOWNLOAD_COMMANDS HTTP/1.0
    # GET /changes/?q=topic:"my-topic"+status:open&o=CURRENT_REVISION&o=DOWNLOAD_COMMANDS HTTP/1.0
    # GET /changes/?q=topic:"my-topic"+(status:open OR status:merged)&o=CURRENT_REVISION&o=DOWNLOAD_COMMANDS HTTP/1.0
    query_string = addGerritQuery('', 'topic', args.topic)
    query_string = addGerritQuery(query_string, 'status', args.status)
    query_string = addGerritQuery(query_string, 'branch', args.branch)
    print('Query string {}'.format(query_string))
    params = {'q': query_string,
              'o': ['CURRENT_REVISION', 'DOWNLOAD_COMMANDS']}

    r = requests.get(url=url_query, params=params)
    content = responseCorrection(r.text)
    data = json.loads(content)

    if args.verbose >= 5:
        pprint.pprint(data)

    return data


def findPathForRepo(args, project_name, repository_name):
    """ Given a project name and repository name search in the
    repo manifest file for it's disk location relative to repo root dir.

    @param args:
    @param project_name:
    @param repository_name:
    @return:
    """
    project_path = REPO_MANIFEST.get((project_name, repository_name), '')

    # Use cached
    if project_path:
        if args.verbose >= 1:
            print('Use cached project path {}'.format(project_path))
        return project_path

    # Parse the xml
    tree = ET.parse(args.manifest)
    root = tree.getroot()
    for element in root.findall('project'):
        if args.verbose >= 5:
            print(element.tag, element.attrib)

        # TODO add parameter for remote name, default to project_name here
        remote_name = element.get('remote')
        path = element.get('path')

        if remote_name == project_name:
            if path.split('/')[-1] == repository_name:
                project_path = os.path.join(args.repo_root_dir, path)
                print('Disk path {}'.format(project_path))
                # Cache entry
                REPO_MANIFEST[(project_name, repository_name)] = project_path

    return project_path


def extractDownloadCommand(args, change):
    rev = change.get('revisions')
    key = list(rev.keys())[0]
    command = rev.get(key)
    command = command.get('fetch')
    command = command.get('anonymous http')
    command = command.get('commands')
    command = command.get(args.download_strategy, None)
    if not command:
        raise Exception("Can't get command for {} download strategy!".format(
            args.download_strategy))

    return command


def checkSkipChange(args, change_id, max_search_depth=100):
    """ Determine if the change should be skipped.
    Determine based on the Change-Id: in commit message.

    @param args: Parsed args
    @param change_id: A gerrit Change-Id to be skipped
    @param max_search_depth: Limit the search depth to a certain number
                             to speed up things.

    @return: True if the change should be skipped
    """
    cmd = ['git', 'rev-list', 'HEAD', '--count']
    output = subprocess.check_output(
        cmd
        , errors="strict").strip()
    rev_count = int(output)

    if args.verbose >= 6:
        print(rev_count)

    # TODO param for max_search_depth
    for i in range(min(rev_count - 1, max_search_depth)):
        cmd = ['git', 'rev-list', '--format=%B', '--max-count',
               '1', 'HEAD~{}'.format(i)]
        output = subprocess.check_output(
            cmd
            , errors="strict").strip()
        if args.verbose >= 6:
            print(output)

        # TODO avoid false positives, search just last occurrence
        if 'Change-Id: {}'.format(change_id) in output:
            print('Found {} in git log'.format(change_id))
            return True

    return False


def validateHandleRepoArgs(args):
    """ Validate args for repositories that use Repo tool

    @param args: Args from ArgumentParser
    """
    print('Using manifest {}'.format(args.manifest))
    if not os.path.exists(args.manifest):
        print('{} does not exist'.format(args.manifest))
        exit(1)

    print('Using repo root dir {}'.format(args.repo_root_dir))
    if not os.path.exists(args.repo_root_dir):
        print('{} does not exist'.format(args.repo_root_dir))
        exit(1)

    print('Using gerrit {}'.format(args.gerrit))
    print('Using download strategy {}'.format(args.download_strategy))
    print('Using review statuses {}'.format(args.status))

    if args.merge_fixer:
        if os.path.exists(args.merge_fixer):
            print('Using script to attempt automatic merge conflicts '
                  'resolution: {}'.format(args.merge_fixer))
        else:
            print('File {} does not exist'.format(args.merge_fixer))
            exit(1)


def handleRepo(args):
    """ Main logic for repositories that use repo tool

    @param args: Args from ArgumentParser
    """
    validateHandleRepoArgs(args)
    tool_cwd = os.getcwd()

    # Get changes
    json_changes = queryChanges(args)

    for json_change in json_changes:
        # Get project of the change
        project = json_change.get('project')
        project_name, repository_name = project.split('/')
        change_id = json_change.get('change_id')
        print('Detected change number {} ID {} project {} repository {}'
              ''.format(json_change.get('_number', ''),
                        change_id,
                        project_name,
                        repository_name))

        # Get path on disk
        project_path = findPathForRepo(args, project_name, repository_name)

        # Get download command
        download_command = extractDownloadCommand(args, json_change)

        # TODO decide if ignore errors or raise exception
        if project_path:
            # cd to path
            os.chdir(project_path)
            print("Changed working directory to: {}".format(os.getcwd()))

            # Check if the change should be skipped
            if args.avoid_re_download and checkSkipChange(args, change_id):
                print('Skipping {}'.format(change_id))
                continue

            # Apply commit
            cmds = download_command.split('&&')
            print('Commands to be executed {}'.format(cmds))
            try:
                for cmd in list(cmds):
                    cmd = cmd.strip('"')
                    print('Command to be executed {}'.format(cmd))

                    if not args.dry_run:
                        output = subprocess.check_output(
                            cmd
                            , errors="strict", shell=True).strip()

                        print('Executed: \n{}'.format(output))
            except Exception as e:
                pprint.pprint(e)
                if args.merge_fixer and not args.dry_run:
                    print('Using merge fixer!')
                    runMergeFixer(args, project_path, tool_cwd)
                else:
                    exit(1)


def runMergeFixer(args, project_path, tool_cwd):
    # TODO support arbitrary location of script

    # Copy fixer to cwd
    src_fixer = '{}'.format(os.path.join(tool_cwd, args.merge_fixer))
    dst_fixer = '{}'.format(os.path.join(project_path, args.merge_fixer))
    cmd = ['cp', src_fixer, dst_fixer]
    run_cmd(cmd, shell=False, halt_on_exception=True)

    # Fix script permissions
    os.chmod(dst_fixer, 0o755)

    # Run fixer
    cmd = [dst_fixer]
    fixer_rc, _ = run_cmd(cmd, shell=False, halt_on_exception=False)

    # Remove fixer
    cmd = ['rm', dst_fixer]
    run_cmd(cmd, shell=False, halt_on_exception=True)

    # Abort in case of fixer run failure
    if fixer_rc == FAILURE:
        print('Fixer failed, aborting!!!')
        exit(1)


def run_cmd(cmd, shell=False, halt_on_exception=False):
    # TODO improve logging, but not worth at the moment.
    # LIMITATION
    # Now we could automate up to doing the cherry-pick continue.
    # `git cherry-pick --continue` opens a text editor and freezes terminal
    # Need to figure a way to go around that.
    try:
        print('Running {}:\n'.format(cmd))

        p1 = subprocess.Popen(
            cmd,
            errors="strict",
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True)
        output, error = p1.communicate()
        print('{}\n'.format(output))
        found_exception = False
        if p1.returncode != 0:
            found_exception = True
    except Exception as e:
        found_exception = True
        pprint.pprint(e)
    finally:
        if found_exception and halt_on_exception:
            exit(1)
        if not found_exception:
            return SUCCESS, output

    return FAILURE, output


def main():
    parser = argparse.ArgumentParser(add_help=False, description='Tool to sync a Gerrit topic',
                                     epilog='''Use %(prog)s subcommand --help to get help for all of parameters''')

    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbosity level')

    subparsers = parser.add_subparsers(title='Repository type control Commands',
                                       help='...')

    # TODO GIT
    repo_parser = subparsers.add_parser('git',
                                        help='Command for handling a git managed project')
    repo_parser.set_defaults(handle=handleList)

    # REPO
    repo_parser = subparsers.add_parser('repo',
                                        help='Command for handling a repo managed project')
    repo_parser.add_argument('--manifest', '-m', help='Path to manifest file', required=False,
                             default=os.path.join(os.getenv('MY_REPO_ROOT_DIR', ''), '.repo/manifests/default.xml'))
    repo_parser.add_argument('--repo-root-dir', '-rr', help='Path to repo root dir', required=False,
                             default=os.getenv('MY_REPO_ROOT_DIR', ''))
    repo_parser.add_argument('--topic', '-t', help='Gerrit topic', required=True)
    repo_parser.add_argument('--gerrit', '-g', help='Gerrit link', required=True)
    repo_parser.add_argument('--dry-run', action='store_true', default=False, help='''Simulate, but don't sync''',
                             required=False)
    repo_parser.add_argument('--download-strategy', '-ds',
                             help='Strategy to download the patch: Pull, Cherry Pick, Branch, Checkout',
                             choices=['Pull', 'Cherry Pick', 'Branch', 'Checkout'], required=True)
    repo_parser.add_argument('--status', '-s', action='append',
                             help='Status of the review',
                             default=[],
                             choices=['open', 'merged', 'abandoned'], required=False)
    repo_parser.add_argument('--branch', '-b', action='append',
                             help='Git branches of the review',
                             default=[], required=False)
    repo_parser.add_argument('--avoid-re-download', '-ard', action='store_true',
                             help='Avoid re-downloading a commit if it already exists in the git repo.',
                             default=False, required=False)
    repo_parser.add_argument('--merge-fixer', '-mf', help='Script to be run to attempt auto merge fixing',
                             required=False)

    repo_parser.set_defaults(handle=handleRepo)

    args = parser.parse_args()

    if hasattr(args, 'handle'):
        args.handle(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
