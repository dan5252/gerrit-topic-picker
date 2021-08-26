# gerrit-topic-picker

## Features for repositories managed by repo tool

- Can filter branch

      topic.py --branch/-b first --branch/-b second ... --branch/-b last

- Can filter status

      topic.py --status/-s open --status/-s merged .. --status/-s whatever

- Can avoid re-downloading a review if a commit with the Change-Id is present

      topic.py --avoid-re-download/-ard

- Specify just one topic

      topic.py --topic target-topic
      topic.py -t target-topic

- Specify gerrit link

      topic.py --gerrit/-g https://my.gerrit/

- Specify download strategy

      topic.py --download-strategy/-ds "Cherry Pick"
      topic.py --download-strategy/-ds "Pull"

- Specify script to be run in case of merge conflict. Script will be copied to the git project path and invoked there.

      topic.py --merge-fixer my_script.sh
      topic.py --merge-fixer my_script.py
      topic.py --merge-fixer my_script.runnable

## Usage for repositories managed by repo tool:

Set the `MY_REPO_ROOT_DIR` environment variable to the repo root directory (the one which contains the `.repo` dir)

    MY_REPO_ROOT_DIR=/path/to/repo/ python3 topic.py repo --help

Example usage in real life:

    MY_REPO_ROOT_DIR=/here \
        python3 topic.py repo \
        --topic my-topic \
        --gerrit https://my.gerrit/ \
        --download-strategy "Cherry Pick" \
        --status open \
        --avoid-re-download
    # OR short
    MY_REPO_ROOT_DIR=/here \
        python3 topic.py repo \
        -t my-topic \
        -g https://my.gerrit/ \
        -ds "Cherry Pick" \
        -s open \
        -ard


    # fails a cherry-pick: CalledProcessError(1, ' git cherry-pick FETCH_HEAD')

    # resolve the cherry-pick merge errors
    # then invoke the tool againg with the same parameters
    # repeat the process until all commits are synced

Example usage for specifying a script that could automatically fix merge conflicts:

    MY_REPO_ROOT_DIR=/here \
        python3 topic.py repo \
        --topic my-topic \
        --gerrit https://my.gerrit/ \
        --download-strategy "Cherry Pick" \
        --status open \
        --avoid-re-download \
        --merge-fixer dummy_merge_fixer.py

Example real life usage with merge fixer that picks changes from both sources:

    MY_REPO_ROOT_DIR=/here \
        python3 topic.py repo \
        --topic my-topic \
        --gerrit https://my.gerrit/ \
        --download-strategy "Cherry Pick" \
        --status open \
        --avoid-re-download \
        --merge-fixer pick_both_merge_fixer.py

Example usage for syncing open and merged reviews:

    MY_REPO_ROOT_DIR=/here \
        python3 topic.py repo \
        --topic my-topic \
        --gerrit https://my.gerrit/ \
        --download-strategy "Cherry Pick" \
        --status open \
        --status merged \
        --avoid-re-download

## Future Work

- Pick relation chain
- Improve merge fixer logging
- Fully automate merge fixer
