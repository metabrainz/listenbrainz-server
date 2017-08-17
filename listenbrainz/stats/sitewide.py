# listenbrainz-server - Server for the ListenBrainz project
#
# Copyright (C) 2017 Param Singh
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

"""
This module contains functions to run queries for sitewide statistics
on Google BigQuery.
"""

from listenbrainz import stats
from listenbrainz import config


def get_artist_count():
    """ Calculates the total number of artists submitted to ListenBrainz.

        Returns:
            artist_count (int)
    """

    query = """SELECT COUNT(DISTINCT(artist_msid)) as artist_count
                 FROM {dataset_id}.{table_id}
            """.format(
                dataset_id=config.BIGQUERY_DATASET_ID,
                table_id=config.BIGQUERY_TABLE_ID,
            )

    return stats.run_query(query)[0]['artist_count']
