import sqlalchemy
import json

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


def pin(pinnedRecording: WritablePinnedRecording):
    """ Inserts a pinned recording record into the database for the user.
        If the user already has an active pinned recording, it will be unpinned before the new one is pinned.

        Args:
            pinnedRecording: An object of class WritablePinnedRecording
    """
    args = {
        'user_id': pinnedRecording.user_id,
        'recording_msid': pinnedRecording.recording_msid,
        'recording_mbid': pinnedRecording.recording_mbid,
        'blurb_content': pinnedRecording.blurb_content,
        'pinned_until': pinnedRecording.pinned_until,
        'created': pinnedRecording.created
    }

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE pinned_recording
               SET pinned_until = NOW()
             WHERE (user_id = :user_id AND pinned_until >= NOW());

            INSERT INTO pinned_recording (user_id, recording_msid, recording_mbid, blurb_content, pinned_until, created)
            VALUES (:user_id, :recording_msid, :recording_mbid, :blurb_content, :pinned_until, :created)
            """), args)


def unpin(user_id: int):
    """ Unpins the currently active pinned recording for the user if they have one.

        Args:
            user_id: the row ID of the user in the DB

        Returns:
            True if an active pinned recording was unpinned,
            False if no pinned recording belonging to the given user_id was currently pinned.
    """

    with db.engine.connect() as connection:
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

    with db.engine.connect() as connection:
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
        row = result.fetchone()
        return PinnedRecording(**dict(row)) if row else None


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
        return [PinnedRecording(**dict(row)) for row in result.fetchall()]


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
        return [PinnedRecording(**dict(row)) for row in result.fetchall()]

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
        count = int(result.fetchone()["value"])
    return count
