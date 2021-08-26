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
    for status_line in out.splitlines():
        if BOTH_ADDED in status_line or BOTH_MODIFIED in status_line:
            # Get file
            conflict_file = status_line.split(':')[1].strip()
            print('Identified conflict file {}'.format(conflict_file))

            with open(conflict_file, "r+") as f:
                # Need to buffer, so file pointer is reset
                buffer = f.readlines()
                f.seek(0)
                for code_line in buffer:
                    # TODO better matching
                    if not code_line.startswith('<<<<<<< ') and \
                            not (code_line.startswith('=======')) and \
                            not code_line.startswith('>>>>>>> '):
                        f.write(code_line)
                    else:
                        print('Dropping :{}'.format(code_line))

                f.truncate()

            # Git add file
            rc, out = run_cmd(['git', 'add', conflict_file])
            if rc != SUCCESS:
                exit(rc)

            # Don't call this, it will freeze the terminal
            continue
            # Git cherry-pick --continue
            rc, out = run_cmd(['git', 'cherry-pick', '--continue'])
            if rc != SUCCESS:
                exit(rc)

# Drop when continue is automated
exit(1)
