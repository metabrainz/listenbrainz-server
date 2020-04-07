#!/bin/bash
# Check if anyting from frontend has been changed
SRC_PATTERN="listenbrainz/webserver/static/js/src"
if ! git diff --cached --name-only | grep --quiet "$SRC_PATTERN" 
then
    exit 0
fi

echo "Linting your code"

# Stash unsaved changes
STASH_NAME=pre-commit-$(date +%s)
git stash save -q --keep-index $STASH_NAME

# Run the linter
./lint.sh

# Pop the changes
STASH_NUM=$(git stash list | grep $STASH_NAME | sed -re 's/stash@\{(.*)\}.*/\1/')
if [ -n "$STASH_NUM" ] 
then
    git stash pop -q stash@{$STASH_NUM}
fi

