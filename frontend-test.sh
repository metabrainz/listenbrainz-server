#!/bin/bash

docker-compose -f docker/docker-compose.test.yml \
               -p listenbrainz_test \
               run --rm frontend_tester npm test
docker-compose -f docker/docker-compose.test.yml \
               -p listenbrainz_test \
               run --rm frontend_tester npm run type-check
docker-compose -f docker/docker-compose.test.yml \
               -p listenbrainz_test \
               run --rm frontend_tester npm run format
