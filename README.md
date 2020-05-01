listenbrainz-server
===================

Server for the ListenBrainz project

[Website](https://listenbrainz.org) |
[Documentation](https://listenbrainz.readthedocs.io) |
[Bug tracker](https://tickets.metabrainz.org/projects/LB/issues)


## About

The ListenBrainz project is similar to the original AudioScrobbler®. Unlike the
original project, ListenBrainz is open source and publishes its data as open
data.

A team of former Last.fm and current MusicBrainz hackers created the first
version of ListenBrainz in a weekend. Since the original project was created,
technology has advanced at an incredibly rapid pace, which made re-creating the
original project fairly straightforward.

The project has two main goals:

1. Allow users to preserve their existing Last.fm® data
2. Make this incredibly useful music usage data available to the world

For more information about this project and its goals, look at our
[website](https://listenbrainz.org/), specifically the
[goals page](https://listenbrainz.org/goals).


## Development environment

These instructions help you get started with the development process.
Installation in a production environment may be different.

**Read the [development environment
documentation](https://listenbrainz.readthedocs.io/en/latest/dev/devel-env.html
"Setting up a development environment - ListenBrainz documentation")**

In order to work with Spark, you'll have to setup the Spark development environment.
Read the [documentation](https://listenbrainz.readthedocs.io/en/latest/dev/spark-devel-env.html).

## Documentation

Full documentation for the ListenBrainz API is available at
[listenbrainz.readthedocs.org](https://listenbrainz.readthedocs.org). You can
also build the documentation locally:

    cd listenbrainz-server/docs
    pip install -r requirements.txt
    make clean html


## License Notice

```
listenbrainz-server - Server for the ListenBrainz project

Copyright (C) 2017 MetaBrainz Foundation Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
```

