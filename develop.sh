#!/bin/bash

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
fi

# Warn user if no arguments passed to develop.sh
if [ "$#" == 0 ]; then
	echo "No arguments provided"
	exit -1
fi

function invoke_docker_compose {
	if [ "$#" -ne 1 ]; then
		echo -e "Function argument to invoke docker-compose is either missing or\nnumber of arguments passed is greater than 1."
		exit -1
	fi
	docker-compose -f docker/docker-compose.yml \
						-p listenbrainz \
						$1
}

function invoke_manage {
	if [ "$#" == 0 ]; then
		echo "Function argument to invoke manage.py is missing."
		exit -1
	fi
	docker-compose -f docker/docker-compose.yml \
						-p listenbrainz \
						run --rm web \
						python3 manage.py $@
}

function open_psql_shell {
	docker exec -it listenbrainz_web_1 psql \
					-U listenbrainz  \
					-h db listenbrainz
}

# Arguments following "manage" are as it is passed to function "invoke_manage" and executed.
# Check on each argument of manage.py is not performed here because with manage.py, develop.sh will expand too.
# Also, if any of the arguments passed to develop.sh which invoke manage.py are incorrect, exception would be raised by manage.py
# so we may skip extra checks in here.
if [ "$1" == "manage" ]; then shift
	if [ -z "$1" ]; then
		echo "Pass a command to invoke manage.py. Try manage.py --help."
		exit -1
	else
		invoke_manage $@
		exit 0
	fi

elif [ "$#" == 1 ]; then
# This argument should only be passed when the containers are up and running i.e. after ./develop.sh up
	if [ "$@" == "psql" ]; then
		echo "Entering into PSQL shell to query DB..."
		open_psql_shell
		exit 0

	elif [ "$@" == "build" ]; then
		echo "Building services..."
		invoke_docker_compose build
		exit 0

	elif [ "$@" == "down" ]; then
		echo "Stopping and removing containers..."
		invoke_docker_compose down
		exit 0

	elif [ "$@" == "up" ]; then
		echo "Creating and starting containers..."
		invoke_docker_compose up
		exit 0

	elif [ "$@" == "stop" ]; then
		echo "Stopping services..."
		invoke_docker_compose stop
		exit 0

	else
		echo "Trying to run the passed command..."
		invoke_docker_compose $@
		exit 0
	fi

else
	echo "Not a valid command"
	exit -1
fi
