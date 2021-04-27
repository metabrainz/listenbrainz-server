#!/bin/bash

function retry {
    local attempts_remaining=5
    local delay=15
    local exit_status=0

    while true; do
        if "$@"; then
            return
        else
            exit_status=$?
        fi

        (( attempts_remaining-- )) || :
        if [ $attempts_remaining -gt 0 ]; then
            echo "Command failed with exit status $exit_status: retrying in ${delay}s"
            sleep $delay
            (( delay *= 2 )) || :
        else
            echo 'Failed to execute command after 5 attempts'
            break
        fi
    done

    return $exit_status
}
