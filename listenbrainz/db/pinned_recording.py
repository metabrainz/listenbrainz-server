import sqlalchemy
import json

from listenbrainz import db
from listenbrainz.db.model.pinned_recording import PinnedRecording
from typing import List

PINNED_REC_GET_COLUMNS = ['user_id', 'recording_mbid::text', 'blurb_content', 'pinned_until',
                          'created']


def pin(pinnedRecording: PinnedRecording):
    """ Inserts a pinned recording record into the database for the user.
        If the user already has an active pinned recording, it will be unpinned before the new one is pinned.

        Args:
            pinnedRecording: An object of class PinnedRecording
    """
    args = {
        'user_id': pinnedRecording.user_id,
        'recording_mbid': pinnedRecording.recording_mbid,
        'blurb_content': pinnedRecording.blurb_content,
        'pinned_until': pinnedRecording.pinned_until,
        'created': pinnedRecording.created
    }

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE pinned_recording
               SET pinned_until = NOW()
             WHERE (user_id = :user_id AND pinned_until > NOW());

            INSERT INTO pinned_recording (user_id, recording_mbid, blurb_content, pinned_until, created)
            VALUES (:user_id, :recording_mbid, :blurb_content, :pinned_until, :created)
            """), args)


def unpin(user_id: int):
    """ Unpins the currently active pinned recording for the user if they have one.

        Args:
            user_id: the row ID of the user in the DB
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE pinned_recording
               SET pinned_until = NOW()
             WHERE (user_id = :user_id AND pinned_until > NOW())
            """), {
            'user_id': user_id,
            }
        )


def delete(pinnedRecording: PinnedRecording):
    """ Deletes the pinned recording record for the user from the database.

        Args:
            pinnedRecording: An validated object of class PinnedRecording
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM pinned_recording
             WHERE user_id = :user_id
               AND recording_mbid = :recording_mbid
               AND created = :created
            """), {
            'user_id': pinnedRecording.user_id,
            'recording_mbid': pinnedRecording.recording_mbid,
            'created': pinnedRecording.created,
            }
        )


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
              FROM pinned_recording
             WHERE (user_id = :user_id
               AND pinned_until > NOW())
            """.format(columns=','.join(PINNED_REC_GET_COLUMNS))), {'user_id': user_id})
        row = result.fetchone()
        return PinnedRecording(**dict(row)) if row else None


def get_pin_history_for_user(user_id: int, count: int, offset: int) -> List[PinnedRecording]:
    """ Get a list of pinned recording records for the user in descending order of their created date

        Args:
            user_id: the row ID of the user in the DB
            count: number of rows to be returned
            offset: number of pinned recordings to skip from the beginning

        Returns:
            A list of PinnedRecording objects sorted by newest to oldest creation date.
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM pinned_recording
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


def get_pin_count_for_user(user_id: int) -> int:
    """ Get the total number pinned_recordings for the user.

        Args:
            user_id: the row ID of the user in the DB

        Returns:
            The total number of the user's pinned_recording records in the database
    """
    query = "SELECT count(*) AS value FROM pinned_recording WHERE user_id = :user_id"

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), {
            'user_id': user_id,
        })
        count = int(result.fetchone()["value"])
    return count
