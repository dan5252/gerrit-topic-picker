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


def responseCorrection(content):
    return content[5:]


def handleList(args):
    pass


def queryChanges(args):
    # TODO: only open, only merged, both
    query = 'changes/'
    url_query = urllib.parse.urljoin(args.gerrit, query)

    if args.verbose:
        print('Query {}'.format(url_query))

    # GET /changes/?q=topic:"my-topic"&o=CURRENT_REVISION&o=DOWNLOAD_COMMANDS HTTP/1.0
    params = {'q': 'topic:"{}"'.format(args.topic),
              'o': ['CURRENT_REVISION', 'DOWNLOAD_COMMANDS']}

    # TODO filter branch
    r = requests.get(url=url_query, params=params)
    content = responseCorrection(r.text)
    data = json.loads(content)

    if args.verbose:
        pprint.pprint(data)

    return data


def findPathForRepo(args, project_name, repository_name):
    project_path = ''
    # TODO parse once
    # Parse the xml
    tree = ET.parse(args.manifest)
    root = tree.getroot()
    for element in root.findall('project'):
        if args.verbose:
            print(element.tag, element.attrib)

        # TODO add parameter for remote name, default to project_name here
        remote_name = element.get('remote')
        path = element.get('path')

        if remote_name == project_name:
            if path.split('/')[-1] == repository_name:
                project_path = os.path.join(args.repo_root_dir, path)
                print('Disk path {}'.format(project_path))

    return project_path


def extractDownloadCommand(args, change):
    rev = change.get('revisions')
    key = list(rev.keys())[0]
    command = rev.get(key)
    command = command.get('fetch')
    command = command.get('anonymous http')
    command = command.get('commands')
    command = command.get(args.strategy, None)
    if not command:
        raise Exception('''Can't get command for {} strategy!'''.format(
            args.strategy))
    # TODO for cherry-pick need to check if it already exists
    # command = command.get('Cherry Pick')

    return command


def handleRepo(args):
    # TODO validations
    print('Using manifest {}'.format(args.manifest))
    if not os.path.exists(args.manifest):
        print('{} does not exist'.format(args.manifest))
        exit(1)

    print('Using repo root dir {}'.format(args.repo_root_dir))
    if not os.path.exists(args.repo_root_dir):
        print('{} does not exist'.format(args.repo_root_dir))
        exit(1)

    print('Using gerrit {}'.format(args.gerrit))
    print('Using strategy {}'.format(args.strategy))

    # Get changes
    json_changes = queryChanges(args)

    for json_change in json_changes:
        # Get project of the change
        project = json_change['project']
        project_name, repository_name = project.split('/')
        print('Detected change {} project {} repository {}'.format(
            json_change.get('_number', ''), project_name, repository_name))
        download_command = extractDownloadCommand(args, json_change)

        # Get path on disk
        project_path = findPathForRepo(args, project_name, repository_name)

        # TODO decide if ignore errors or raise exception
        if project_path:
            # cd to path
            os.chdir(project_path)
            print("Changed working directory to: {}".format(os.getcwd()))

            # Apply commit
            try:
                cmd = download_command.split(' ')
                cmd = [x.strip('"') for x in cmd]
                print('Command to be executed {}'.format(cmd))

                if not args.dry_run:
                    output = subprocess.check_output(
                        cmd
                        , errors="strict").strip()

                    print('Executed: \n{}'.format(output))
            except Exception as e:
                pprint.pprint(e)
                exit(1)


def main():
    parser = argparse.ArgumentParser(add_help=False, description='Tool to sync a Gerrit topic',
                                     epilog='''Use %(prog)s subcommand --help to get help for all of parameters''')

    # TODO add verbosity level
    parser.add_argument('--verbose', '-v', action='store_true', help='verbose mode')

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
    repo_parser.add_argument('--strategy', '-s',
                             help='Strategy to download the patch: Pull, Cherry Pick, Branch, Checkout',
                             choices=['Pull', 'Cherry Pick', 'Branch', 'Checkout'], required=True)

    repo_parser.set_defaults(handle=handleRepo)

    args = parser.parse_args()

    if hasattr(args, 'handle'):
        args.handle(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
