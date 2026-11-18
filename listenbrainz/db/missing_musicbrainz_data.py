# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2020 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import orjson
import sqlalchemy
import uuid

from datetime import datetime, timedelta, timezone
from listenbrainz import db
from pydantic import ValidationError

from data.model.user_missing_musicbrainz_data import (UserMissingMusicBrainzData,
                                                      UserMissingMusicBrainzDataJson, UserMissingMusicBrainzDataRecord)
from flask import current_app

from listenbrainz.db.mbid_manual_mapping import check_manual_mapping_exists


ALLOWLISTED_ADDITIONAL_INFO_KEYS = (
    "spotify_id",
    "spotify_album_id",
    "youtube_id",
    "apple_music_id",
    "apple_album_id",
    "origin_url",
    "music_service",
    "music_service_name",
)

SERVICE_METADATA_CHUNK_SIZE = 1000

SERVICE_METADATA_TOLERANCE_CHUNK_SIZE = 8


def insert_user_missing_musicbrainz_data(db_conn, user_id: int,
                                         missing_musicbrainz_data: UserMissingMusicBrainzDataJson, source: str):
    """ Insert missing musicbrainz data that a user has submitted to ListenBrainz but
        has not submitted to MusicBrainz in the db.

        Args:
            db_conn: database connection
            user_id : row id of the user.
            missing_musicbrainz_data : Data that is submitted to ListenBrainz by the users
                   but is not submitted to MusicBrainz.
            source : Source of generation of missing MusicBrainz data.
    """
    db_conn.execute(sqlalchemy.text("""
        INSERT INTO missing_musicbrainz_data (user_id, data, source)
             VALUES (:user_id, :missing_musicbrainz_data, :source)
        ON CONFLICT (user_id)
      DO UPDATE SET user_id = :user_id,
                    data = :missing_musicbrainz_data,
                    source = :source,
                    created = NOW()
        """), {
            'user_id': user_id,
            'missing_musicbrainz_data': orjson.dumps(missing_musicbrainz_data.dict()).decode("utf-8"),
            'source': source
        }
    )
    db_conn.commit()


def get_user_missing_musicbrainz_data(db_conn, listens_conn, user_id: int, source: str):
    """ Get missing musicbrainz data that has not been submitted to LB
        for a user with the given row ID.

        Args:
            db_conn: database connection
            listens_conn: listens database connection
            user_id: the row ID of the user in the DB
            source : Source of generation of missing MusicBrainz data.

        Returns:
            A tuple of the following format
            (
                'missing_musicbrainz_data'  (dict): missing musicbrainz data,
                'created' (datetime): datetime object representing when the missing
                                      MusicBrainz data for this user was last updated.
            )

        A sample response would look like:
            ([
                {
                    "artist_name": "Katty Peri"
                    "listened_at": 1588204593,
                    "recording_msid": "568eeea3-9255-4878-9df8-296043344e04",
                    "release_name": "No Place Is Home",
                    "track_name": "How High"
                },
                {
                    "artist_name": "Welshly Arms",
                    "listened_at": 1588204583,
                    "recording_msid": "b911620d-8541-44e5-a0db-977679efb37d",
                    "release_name": "No Place Is Home",
                    "track_name": "Sanctuary"
                }
            ], datetime.datetime(2020, 5, 1, 10, 0, 0))

    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT user_id, data, created
          FROM missing_musicbrainz_data
         WHERE user_id = :user_id
           AND source = :source
        """), {
                'user_id': user_id,
                'source': source
            }
    )
    row = result.mappings().first()

    try:
        if row:
            missing_mb_data = UserMissingMusicBrainzDataJson(missing_musicbrainz_data=row["data"]["missing_musicbrainz_data"]).missing_musicbrainz_data
            if missing_mb_data:
                remaining_data = remove_mapped_mb_data(listens_conn, user_id, missing_mb_data)
                return add_service_metadata(listens_conn, user_id, remaining_data), row["created"]
            return None, row["created"]
        else:
            return None, None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting missing musicbrainz data for source "{source}"
                                 for user with user_id: {user_id}. Data: {data}""".format(source=source, user_id=user_id,
                                 data=orjson.dumps(row['data'], option=orjson.OPT_INDENT_2)), exc_info=True)
        return None, None


def remove_mapped_mb_data(listens_conn, user_id: int, missing_musicbrainz_data: list[UserMissingMusicBrainzDataRecord]):
    """ Remove musicbrainz data that has been mapped to MusicBrainz by the user.

        Args:
            listens_conn: listens database connection
            user_id: LB user id.
            missing_musicbrainz_data: List of missing musicbrainz data.

        Returns:
            List of missing musicbrainz data that has not been mapped to MusicBrainz.
    """
    missing_data_map = {r.recording_msid: r for r in missing_musicbrainz_data}
    valid_msids = [msid for msid in missing_data_map if _is_valid_uuid(msid)]
    existing_mappings = check_manual_mapping_exists(listens_conn, user_id, valid_msids) if valid_msids else set()

    remaining_data = []
    for item in missing_musicbrainz_data:
        if item.recording_msid not in existing_mappings:
            remaining_data.append(item.dict())

    return remaining_data


def _is_valid_uuid(msid: str) -> bool:
    try:
        uuid.UUID(msid)
    except (ValueError, AttributeError):
        return False
    return True


def _parse_cached_timestamp(listened_at: str):
    """ Parse a cached timestamp into a timezone aware UTC datetime.

        Returns None for unparseable, timezone-naive or out-of-range UTC values,
        which suppresses hydration for that record.

        Args:
            listened_at: ISO timestamp string stored in the missing musicbrainz data cache.
    """
    try:
        cached_at = datetime.fromisoformat(listened_at)
        if cached_at.tzinfo is None:
            return None
        return cached_at.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def _filter_service_metadata(additional_info) -> dict:
    """ Reduce a submitted additional_info object to its allowlisted string values.

        Args:
            additional_info: decoded JSON value of a stored listen's additional_info.

        Returns:
            Dict with at most the allowlisted keys; blank, null, non-string and unknown
            values are omitted.
    """
    if not isinstance(additional_info, dict):
        return {}
    return {key: additional_info[key] for key in ALLOWLISTED_ADDITIONAL_INFO_KEYS
            if isinstance(additional_info.get(key), str) and additional_info[key].strip()}


def _names_match(candidate, record) -> bool:
    """ Compare a stored listen's submitted names with a cached record's names.

        Null and absent release names are equivalent; an empty release name is not.
        No case folding or fuzzy matching: a mismatch conservatively leaves the record
        without service metadata.
    """
    return (candidate["artist_name"] == record["artist_name"]
            and candidate["track_name"] == record["recording_name"]
            and candidate["release_name"] == record.get("release_name"))


def _select_representative_listen(candidates, record, cached_at):
    """ Pick the candidate that is the record's representative listen, if there is one.

        A listen at the exact cached timestamp with matching names is preferred.
        Otherwise a single unambiguous names-matching candidate inside the one
        millisecond window is accepted. Anything ambiguous or mismatching returns None
        and the record stays without service metadata.
    """
    matching = [candidate for candidate in candidates if _names_match(candidate, record)]
    exact = [candidate for candidate in matching if candidate["listened_at"] == cached_at]
    if exact:
        return exact[0]
    if len(matching) == 1:
        return matching[0]
    return None


def add_service_metadata(listens_conn, user_id: int, rows: list[dict]) -> list[dict]:
    """ Attach submitted service metadata from the listens database to missing data records.

        Each record is enriched only from its representative listen: the same user's
        listen at the record's recording msid, cached timestamp and submitted
        artist/recording/release names. Records without a valid msid/timestamp or
        without a matching listen keep their exact legacy shape. The cache itself is
        never modified.

        The lookup runs in two phases, both bound to the (user_id, listened_at,
        recording_msid) index. First an equality probe on the exact cached timestamp,
        which the planner resolves as one index scan per key. Then, only for
        millisecond-aligned cache timestamps without a matching exact listen, a one
        millisecond range probe that covers listen values truncated by the spark job,
        chunked because the planner cannot estimate the range selectivity.

        Args:
            listens_conn: listens database connection
            user_id: LB user id.
            rows: list of missing musicbrainz data dicts.

        Returns:
            The rows, with an allowlisted additional_info object added to records whose
            representative listen carries service metadata.
    """
    exact_pairs = []
    exact_pair_indexes = {}
    row_exact = {}
    row_ms_aligned = {}
    for index, row in enumerate(rows):
        msid = row.get("recording_msid")
        cached_at = _parse_cached_timestamp(row.get("listened_at"))
        if cached_at is None or not _is_valid_uuid(msid):
            continue
        canonical_msid = str(uuid.UUID(msid))
        pair = (canonical_msid, cached_at)
        if pair in exact_pair_indexes:
            pair_index = exact_pair_indexes[pair]
        else:
            pair_index = len(exact_pairs)
            exact_pair_indexes[pair] = pair_index
            exact_pairs.append(pair)
        row_exact[index] = pair_index
        row_ms_aligned[index] = cached_at.microsecond % 1000 == 0

    exact_candidates = [None] * len(exact_pairs)
    for chunk_start in range(0, len(exact_pairs), SERVICE_METADATA_CHUNK_SIZE):
        chunk = exact_pairs[chunk_start:chunk_start + SERVICE_METADATA_CHUNK_SIZE]
        result = listens_conn.execute(sqlalchemy.text("""
            WITH requested AS (
                SELECT *
                  FROM unnest(CAST(:msids AS UUID[]), CAST(:cached_ats AS TIMESTAMPTZ[]))
                    WITH ORDINALITY AS r(msid, cached_at, ordinal)
            )
            SELECT r.ordinal
                 , l.listened_at
                 , l.data->>'artist_name' AS artist_name
                 , l.data->>'track_name' AS track_name
                 , l.data->>'release_name' AS release_name
                 , l.data->'additional_info' AS additional_info
              FROM requested r
              JOIN listen l
                ON l.user_id = :user_id
               AND l.recording_msid = r.msid
               AND l.listened_at = r.cached_at
            """), {
                "user_id": user_id,
                "msids": [pair[0] for pair in chunk],
                "cached_ats": [pair[1] for pair in chunk],
            })
        for candidate in result.mappings():
            exact_candidates[chunk_start + candidate["ordinal"] - 1] = candidate

    tolerance_pairs = []
    tolerance_pair_indexes = {}
    row_tolerance = {}
    for index, pair_index in row_exact.items():
        row = rows[index]
        candidate = exact_candidates[pair_index]
        if candidate is not None and _names_match(candidate, row):
            service_metadata = _filter_service_metadata(candidate["additional_info"])
            if service_metadata:
                row["additional_info"] = service_metadata
            continue
        if not row_ms_aligned[index]:
            continue
        cached_at = exact_pairs[pair_index][1]
        try:
            window_end = cached_at + timedelta(milliseconds=1)
        except OverflowError:
            continue
        triple = (exact_pairs[pair_index][0], cached_at, window_end)
        if triple in tolerance_pair_indexes:
            tolerance_index = tolerance_pair_indexes[triple]
        else:
            tolerance_index = len(tolerance_pairs)
            tolerance_pair_indexes[triple] = tolerance_index
            tolerance_pairs.append(triple)
        row_tolerance[index] = tolerance_index

    tolerance_candidates = [[] for _ in tolerance_pairs]
    for chunk_start in range(0, len(tolerance_pairs), SERVICE_METADATA_TOLERANCE_CHUNK_SIZE):
        chunk = tolerance_pairs[chunk_start:chunk_start + SERVICE_METADATA_TOLERANCE_CHUNK_SIZE]
        result = listens_conn.execute(sqlalchemy.text("""
            WITH requested AS (
                SELECT *
                  FROM unnest(CAST(:msids AS UUID[]), CAST(:starts AS TIMESTAMPTZ[]), CAST(:ends AS TIMESTAMPTZ[]))
                    WITH ORDINALITY AS r(msid, window_start, window_end, ordinal)
            )
            SELECT r.ordinal
                 , l.listened_at
                 , l.data->>'artist_name' AS artist_name
                 , l.data->>'track_name' AS track_name
                 , l.data->>'release_name' AS release_name
                 , l.data->'additional_info' AS additional_info
              FROM requested r
              JOIN listen l
                ON l.user_id = :user_id
               AND l.recording_msid = r.msid
               AND l.listened_at >= r.window_start
               AND l.listened_at < r.window_end
            """), {
                "user_id": user_id,
                "msids": [triple[0] for triple in chunk],
                "starts": [triple[1] for triple in chunk],
                "ends": [triple[2] for triple in chunk],
            })
        for candidate in result.mappings():
            tolerance_candidates[chunk_start + candidate["ordinal"] - 1].append(candidate)

    for index, tolerance_index in row_tolerance.items():
        row = rows[index]
        representative = _select_representative_listen(
            tolerance_candidates[tolerance_index], row, tolerance_pairs[tolerance_index][1])
        if representative is None:
            continue
        service_metadata = _filter_service_metadata(representative["additional_info"])
        if service_metadata:
            row["additional_info"] = service_metadata

    return rows
