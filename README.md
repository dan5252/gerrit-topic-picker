# gerrit-topic-picker

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

## Future Work

- Pick relation chain
