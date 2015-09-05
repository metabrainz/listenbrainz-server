
## Development

    $ PYTHONPATH=. bin/listenstore-test.py

## Pip, eggs, etc

    $ make dist

then install the egg

## Schema

Cassandra table called "listens" stores everything. It is keyed on `(uid,
idkey)`, where idkey is the first 3 numbers in the unixtimestamp of the
listen.

This effectively shards listens by a user over multiple row keys, since
very wide rows are inefficient.

This works out at 115 days of listening data per row key, or 333,333
listens if a user is listening continually with 30sec long tracks.

