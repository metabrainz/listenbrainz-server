## Useful commands

Here are some notes for short-cuts to get useful things done while hacking on ListenBrainz:

### Redis

To open a Redis command prompt:

    docker exec -it listenbrainz_redis_1 redis-cli


### Postgres

To get a postgres command prompt:

    ./develop.sh psql


### Timescale

To get a timescale/postgres command prompt:

    ./develop.sh timescale


### Tests

To run the unit tests:

    ./test.sh

To run the integration tests:

    ./test.sh int
