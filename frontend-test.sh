#!/bin/bash

# ./frontend-test.sh                    Run tests
# ./frontend-test.sh -u                 Run tests, update snapshots
# ./frontend-test.sh -b                 Build containers

if [ "$1" == "-u" ]; then
    docker-compose -f docker/docker-compose.test.yml \
       -p listenbrainz_test \
       run --rm frontend_tester npm run test:update-snapshots
    exit 0
fi

if [ "$1" == "-b" ]; then
    docker-compose -f docker/docker-compose.test.yml -p listenbrainz_test build
    exit 0
fi

docker-compose -f docker/docker-compose.test.yml \
               -p listenbrainz_test \
               run --rm frontend_tester npm test
