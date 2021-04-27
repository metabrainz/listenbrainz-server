#!/bin/bash

retry() {
    local attempts_remaining=5
    local delay=15
    while true; do
        "$@"
        status=$?
        if [[ $status -eq 0 ]]; then
            break
        fi
        let 'attempts_remaining -= 1'
        if [[ $attempts_remaining -gt 0 ]]; then
            echo "Command failed with exit status $status; retrying in $delay seconds"
            sleep $delay
            let 'delay *= 2'
        else
            echo 'Failed to execute command after 5 attempts'
            break
        fi
    done
}
