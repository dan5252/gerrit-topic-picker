#!/usr/bin/python3
import os
import pprint
import subprocess

CHERRY_PICKING = 'You are currently cherry-picking commit'
BOTH_ADDED = 'both added:'
BOTH_MODIFIED = 'both modified:'

SUCCESS = 0
FAILURE = 1


# TODO improve, but not worth at the moment because
# `git cherry-pick --continue` opens a text editor and freezes terminal
# Need to figure a way to go around that.
def run_cmd(cmd, shell=False, halt_on_exception=False):
    try:
        print('Running {}:\n'.format(cmd))

        output = subprocess.check_output(
            cmd
            , errors="strict", shell=shell).strip()
        found_exception = False
    except Exception as e:
        found_exception = True
        pprint.pprint(e)
    finally:
        if found_exception and halt_on_exception:
            exit(1)
        if not found_exception:
            return SUCCESS, output

    return FAILURE, None


print('CWD {}'.format(os.getcwd()))

rc, out = run_cmd(['git', 'status'])
if rc != SUCCESS:
    exit(rc)

if CHERRY_PICKING in out:
    print('Detected cherry-picking {}'.format(os.getcwd()))
    for line in out.splitlines():
        if BOTH_ADDED in line or BOTH_MODIFIED in line:
            # Get file
            file = line.split(':')[1].strip()
            print('Identified file {}'.format(file))

            # TODO remove the artifact lines for merge (<<<,===,>>>)

            # Git add file
            rc, out = run_cmd(['git', 'add', file])
            if rc != SUCCESS:
                exit(rc)

            # Don't call this, it will freeze the terminal
            continue
            # Git cherry-pick --continue
            rc, out = run_cmd(['git', 'cherry-pick', '--continue'])
            if rc != SUCCESS:
                exit(rc)

exit(1)
