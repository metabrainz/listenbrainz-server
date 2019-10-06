#!/bin/bash

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
fi

function invoke_docker_compose {
	docker-compose -f docker/docker-compose.yml \
						-p listenbrainz \
						"$@"
}

function invoke_manage {
	invoke_docker_compose run --rm web \
							python3 manage.py \
							"$@"
}

function open_psql_shell {
	invoke_docker_compose run --rm web psql \
							-U listenbrainz  \
							-h db listenbrainz
}
# Arguments following "manage" are as it is passed to function "invoke_manage" and executed.
# Check on each argument of manage.py is not performed here because with manage.py, develop.sh will expand too.
# Also, if any of the arguments passed to develop.sh which invoke manage.py are incorrect, exception would be raised by manage.py
# so we may skip extra checks in here.
if [ "$1" == "manage" ]; then shift
	echo "Invoking manage.py..."
	invoke_manage "$@"

elif [ "$1" == "psql" ]; then
	echo "Entering into PSQL shell to query DB..."
	open_psql_shell

else
	echo "Trying to run the passed command with docker-compose..."
	invoke_docker_compose "$@"
fi
