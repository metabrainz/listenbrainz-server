
## Development
    $ PYTHONPATH=. bin/listenstore-test.py

## Pip, eggs, etc

    $ RELEASE_VERSION=0.1.0 make dist

then install the egg:

    $ easy_install ./dist/listenbrainz_store-0.1.0-py2.7.egg

bin scripts get installed to `/usr/local/bin`.

## Configuration
Listenstore uses same configuration file as used for ListenBrainz. If the
location of the `config.py` is changed, the change them to appropriate values.

## Schema

Postgres table called "listens" stores everything. It is keyed on `(user_id,
ts)`, where ts is the timestamp (with timezone) of the listen.

This effectively shards listens by a user over multiple row keys, since
very wide rows are inefficient.

This works out at 115 days of listening data per row key, or 333,333
listens if a user is listening continually with 30sec long tracks.

