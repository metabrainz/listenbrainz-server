## Useful commands

Here are some notes for short-cuts to get useful things done while hacking on ListenBrainz:

### Redis

To open a Redis command prompt:

    docker exec -it docker_redis_1 redis-cli


### Influx

To open an Influxdb command prompt:

    docker exec -it docker_influx_1 influx

and to drop all the listens in influx db:

    use listenbrainz
    drop measurement listen


### Postgres

To get a postgres command prompt:

    docker exec -it docker_web_1 psql -U listenbrainz -h db listenbrainz
