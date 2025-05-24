""" This module contains data dump creation and import functions.

Read more about the data dumps in our documentation here:
https://listenbrainz.readthedocs.io/en/latest/users/listenbrainz-dumps.html
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


import os
from datetime import datetime

from psycopg2.sql import Identifier, SQL

from listenbrainz.dumps import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.dumps.exporter import zstd_dump
from listenbrainz.dumps.models import DumpTable, DumpFormat, DumpTablesCollection, DumpEngineName
from listenbrainz.utils import create_path


MAPPING_TABLES = [
    DumpTable(
        table_name=Identifier("mapping", "canonical_musicbrainz_data"),
        filename="canonical_musicbrainz_data.csv",
        file_format=DumpFormat.csv,
        columns=(
            "id",
            "artist_credit_id",
            SQL("array_to_string(artist_mbids, ',') AS artist_mbids"),
            "artist_credit_name",
            "release_mbid",
            "release_name",
            "recording_mbid",
            "recording_name",
            "combined_lookup",
            "score",
        )
    ),
    DumpTable(
        table_name=Identifier("mapping", "canonical_recording_redirect"),
        filename="canonical_recording_redirect.csv",
        file_format=DumpFormat.csv,
        columns=(
            "recording_mbid",
            "canonical_recording_mbid",
            "canonical_release_mbid"
        )
    ),
    DumpTable(
        table_name=Identifier("mapping", "canonical_release_redirect"),
        filename="canonical_release_redirect.csv",
        file_format=DumpFormat.csv,
        columns=(
            "release_mbid",
            "canonical_release_mbid",
            "release_group_mbid"
        )
    )
]


def create_mapping_dump(location: str, dump_time: datetime, use_lb_conn: bool):
    """ Create postgres database dump of the mapping supplemental tables. """
    tables_collection = DumpTablesCollection(
        engine_name=DumpEngineName.ts if use_lb_conn else DumpEngineName.mb,
        tables=MAPPING_TABLES
    )

    archive_name = "musicbrainz-canonical-dump-{time}".format(
        time=dump_time.strftime("%Y%m%d-%H%M%S")
    )

    metadata = {"TIMESTAMP": dump_time}
    with zstd_dump(location, archive_name, metadata, DUMP_DEFAULT_THREAD_COUNT) as (zstd, tar, temp_dir, archive_path):
        archive_tables_dir = os.path.join(temp_dir, "canonical")
        create_path(archive_tables_dir)

        tables_collection.dump_tables(archive_tables_dir)

        for table in tables_collection.tables:
            tar.add(
                os.path.join(archive_tables_dir, table.filename),
                arcname=os.path.join(archive_name, "canonical", table.filename)
            )

    return archive_path
