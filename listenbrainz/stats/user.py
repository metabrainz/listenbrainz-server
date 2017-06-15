"""
This module contains functions that create jobs and retrieve stats about users
from Google BigQuery
"""
import listenbrainz.config as config
import json
from listenbrainz import stats


def get_top_tracks(musicbrainz_id, time_interval=None):
    """ Get top tracks of user with given MusicBrainz ID over a particular time interval

        Args:
            musicbrainz_id (str): The MusicBrainz ID of the user
            time_interval  (str): Interval in the BigQuery interval format which can be seen here:
            https://cloud.google.com/bigquery/docs/reference/standard-sql/functions-and-operators#timestamp_sub

        Returns:
            sorted list of the following format
            [
                {
                    "track_name" (str)
                    "recording_msid" (uuid)
                    "artist_name" (str)
                    "artist_msid" (uuid)
                    "listen_count" (int)
                }
            ]
    """

    filter_str = ""
    if time_interval:
        filter_str = "AND listened_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {})".format(time_interval)

    # construct the query string
    query = """SELECT artist_name
                    , artist_msid
                    , recording_msid
                    , track_name
                    , COUNT(recording_msid) as listen_count
                 FROM {dataset_id}.{table_id}
                WHERE user_name = @username
                {time_filter_clause}
             GROUP BY recording_msid, track_name, artist_name, artist_msid
             ORDER BY listen_count DESC
            """.format(
                dataset_id=config.BIGQUERY_DATASET_ID,
                table_id=config.BIGQUERY_TABLE_ID,
                time_filter_clause=filter_str,
            )

    # construct the parameters that must be passed to the Google BigQuery API

    # start with a list of parameters to pass and then convert it to standard format
    # required by Google BigQuery
    parameters = [
        {
            "name": "username",
            "type": "STRING",
            "value": musicbrainz_id,
        },
    ]

    return stats.run_query(query, parameters)

