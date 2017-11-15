""" This module contains a click group with commands to
create and import postgres data dumps.
"""

# listenbrainz-server - Server for the ListenBrainz project
#
# Copyright (C) 2017 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import click
import listenbrainz.db.dump as db_dump
import os

from listenbrainz import config
from listenbrainz import db


cli = click.Group()

@cli.command()
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int)
def create(location, threads):
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    db_dump.dump_postgres_db(location, threads)


@cli.command()
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
def import_dump(location):
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    db_dump.import_postgres_dump(location)
