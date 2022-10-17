import sqlalchemy
from datetime import datetime

from listenbrainz import db
from listenbrainz.db.model.pinned_recording import PinnedRecording, WritablePinnedRecording
from typing import List


PINNED_REC_GET_COLUMNS = [
    "user_id",
    "pin.id AS row_id",
    "recording_msid::text",
    "recording_mbid::text",
    "blurb_content",
    "pinned_until",
    "pin.created as created",
]


def pin(pinned_recording: WritablePinnedRecording):
    """ Inserts a pinned recording record into the database for the user.
        If the user already has an active pinned recording, it will be unpinned before the new one is pinned.

        Args:
            pinned_recording: An object of class WritablePinnedRecording

        Returns:
            a PinnedRecording based on the input argument with the addition of a user_id field
    """
    args = {
        'user_id': pinned_recording.user_id,
        'recording_msid': pinned_recording.recording_msid,
        'recording_mbid': pinned_recording.recording_mbid,
        'blurb_content': pinned_recording.blurb_content,
        'pinned_until': pinned_recording.pinned_until,
        'created': pinned_recording.created
    }

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE pinned_recording
               SET pinned_until = NOW()
             WHERE (user_id = :user_id AND pinned_until >= NOW())
        """), {"user_id": pinned_recording.user_id})

        result = connection.execute(sqlalchemy.text("""
            INSERT INTO pinned_recording (user_id, recording_msid, recording_mbid, blurb_content, pinned_until, created)
                 VALUES (:user_id, :recording_msid, :recording_mbid, :blurb_content, :pinned_until, :created)
              RETURNING (id)
            """), args)

        row_id = result.fetchone().id
        pinned_recording.row_id = row_id
        return PinnedRecording.parse_obj(pinned_recording.dict())


def unpin(user_id: int):
    """ Unpins the currently active pinned recording for the user if they have one.

        Args:
            user_id: the row ID of the user in the DB

        Returns:
            True if an active pinned recording was unpinned,
            False if no pinned recording belonging to the given user_id was currently pinned.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            UPDATE pinned_recording
               SET pinned_until = NOW()
             WHERE (user_id = :user_id AND pinned_until >= NOW())
            """), {
            'user_id': user_id,
            }
        )
        return result.rowcount == 1


def delete(row_id: int, user_id: int):
    """ Deletes the pinned recording record for the user from the database.

        Args:
            row_id: The row id of the pinned_recording to delete from the DB's 'pinned_recording' table

        Returns:
            True if a pinned recording for the given row_id and user_id was deleted.
            False if the pinned recording for the given row_id and user_id did not exist.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            DELETE FROM pinned_recording
             WHERE id = :row_id
               AND user_id = :user_id
            """), {
            'row_id': row_id,
            'user_id': user_id
            }
        )
        return result.rowcount == 1


def get_current_pin_for_user(user_id: int) -> PinnedRecording:
    """ Get the currently active pinned recording for the user if they have one.

        Args:
            user_id: the row ID of the user in the DB

        Returns:
            A PinnedRecording object.
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM pinned_recording as pin
             WHERE (user_id = :user_id
               AND pinned_until >= NOW())
            """.format(columns=','.join(PINNED_REC_GET_COLUMNS))), {'user_id': user_id})
        row = result.mappings().first()
        return PinnedRecording(**row) if row else None


def get_pin_history_for_user(user_id: int, count: int, offset: int) -> List[PinnedRecording]:
    """ Get a list of pinned recordings for the user in descending order of their created date

        Args:
            user_id: the row ID of the user in the DB
            count: number of pinned recordings to be returned
            offset: number of pinned recordings to skip from the beginning

        Returns:
            A list of PinnedRecording objects sorted by newest to oldest creation date.
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM pinned_recording as pin
             WHERE user_id = :user_id
             ORDER BY created DESC
             LIMIT :count
            OFFSET :offset
            """.format(columns=','.join(PINNED_REC_GET_COLUMNS))), {
            'user_id': user_id,
            'count': count,
            'offset': offset
        })
        return [PinnedRecording(**row) for row in result.mappings()]


def get_pins_for_user_following(user_id: int, count: int, offset: int) -> List[PinnedRecording]:
    """ Get a list of active pinned recordings for all the users that a user follows sorted
        in descending order of their created date.

        Args:
            user_id: the row ID of the main user in the DB
            count: number of pinned recordings to be returned
            offset: number of pinned recordings to skip from the beginning

        Returns:
            A list of PinnedRecording objects sorted by newest to oldest creation date.
    """
    COLUMNS_WITH_USERNAME = PINNED_REC_GET_COLUMNS + ['"user".musicbrainz_id as user_name']

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM user_relationship
              JOIN "user"
                ON user_1 = "user".id
              JOIN pinned_recording as pin
                ON user_1 = pin.user_id
             WHERE user_0 = :user_id
               AND relationship_type = 'follow'
               AND pinned_until >= NOW()
             ORDER BY created DESC
             LIMIT :count
            OFFSET :offset
            """.format(columns=','.join(COLUMNS_WITH_USERNAME))), {
            'user_id': user_id,
            'count': count,
            'offset': offset
        })
        return [PinnedRecording(**row) for row in result.mappings()]


def get_pins_for_feed(user_ids: List[int], min_ts: int, max_ts: int, count: int) -> List[PinnedRecording]:
    """ Gets a list of PinnedRecordings for specified users in descending order of their created date.

    Args:
        user_ids: a list of user row IDs
        min_ts: History before this timestamp will not be returned
        max_ts: History after this timestamp will not be returned
        count: Maximum amount of objects to be returned

    Returns:
        A list of PinnedRecording objects.
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM pinned_recording as pin
             WHERE pin.user_id IN :user_ids
               AND pin.created > :min_ts
               AND pin.created < :max_ts
          ORDER BY pin.created DESC
             LIMIT :count
        """.format(columns=','.join(PINNED_REC_GET_COLUMNS))), {
            "user_ids": tuple(user_ids),
            "min_ts": datetime.utcfromtimestamp(min_ts),
            "max_ts": datetime.utcfromtimestamp(max_ts),
            "count": count,
        })
        return [PinnedRecording(**row) for row in result.mappings()]


def get_pin_by_id(row_id: int) -> PinnedRecording:
    """ Get a pinned_recording by id
        Args:
            row_id: the row ID of the pinned_recording
        Returns:
            PinnedRecording that satisfies the condition
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM pinned_recording as pin
             WHERE pin.id = :row_id
        """.format(columns=','.join(PINNED_REC_GET_COLUMNS))), {
            "row_id": row_id,
        })
        row = result.mappings().first()
        return PinnedRecording(**row) if row else None


def get_pin_count_for_user(user_id: int) -> int:
    """ Get the total number pinned_recordings for the user.

        Args:
            user_id: the row ID of the user in the DB

        Returns:
            The total number of the user's pinned_recording records in the database
    """
    query = """SELECT count(*)
                   AS value
                 FROM pinned_recording
                WHERE user_id = :user_id"""

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), {
            'user_id': user_id,
        })
        count = int(result.fetchone().value)
    return count
