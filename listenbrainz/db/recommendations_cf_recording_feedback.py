import sqlalchemy

from listenbrainz.db.model.recommendation_feedback import (RecommendationFeedbackSubmit,
                                                           RecommendationFeedbackDelete)
from typing import List


def insert(connection, feedback_submit: RecommendationFeedbackSubmit):
    """ Inserts a feedback record for a user's rated recommendation into the database.
        If the record is already present for the user, the rating is updated to the new
        value passed.

        Args:
            feedback_submit: An object of class RecommendationFeedbackSubmit
    """
    connection.execute(sqlalchemy.text("""
        INSERT INTO recommendation_feedback (user_id, recording_mbid, rating, created)
        -- using clock_timestamp because value returned by now() is always fixed during a transaction
        -- this creates issues during tests where we want to depend on events being returned in descending order
             VALUES (:user_id, :recording_mbid, :rating, clock_timestamp())
        ON CONFLICT (user_id, recording_mbid)
      DO UPDATE SET rating = :rating,
                    created = clock_timestamp()
        """), {
            'user_id': feedback_submit.user_id,
            'recording_mbid': feedback_submit.recording_mbid,
            'rating': feedback_submit.rating,
        }
    )


def delete(connection, feedback_delete: RecommendationFeedbackDelete):
    """ Deletes the feedback record for a given recommendation for the user from the database

        Args:
            feedback_delete: An object of class RecommendationFeedbackDelete
    """
    connection.execute(sqlalchemy.text("""
        DELETE FROM recommendation_feedback
         WHERE user_id = :user_id
           AND recording_mbid = :recording_mbid
        """), {
            'user_id': feedback_delete.user_id,
            'recording_mbid': feedback_delete.recording_mbid,
        }
    )


def get_feedback_for_user(connection, user_id: int, limit: int, offset: int, rating: str = None) -> List[RecommendationFeedbackSubmit]:
    """ Get a list of recommendation feedback given by the user in descending order of their creation.
        Feedback will be filtered based on limit, offset and rating, if passed.

        Args:
            user_id: the row ID of the user in the DB
            rating: the rating value by which the results are to be filtered.
            limit: number of rows to be returned
            offset: number of feedback to skip from the beginning

        Returns:
            A list of Feedback objects
    """

    args = {"user_id": user_id, "limit": limit, "offset": offset}
    query = """ SELECT user_id,
                       recording_mbid::text,
                       rating,
                       created
                  FROM recommendation_feedback
                 WHERE user_id = :user_id """

    if rating:
        query += " AND rating = :rating"
        args["rating"] = rating

    query += """ ORDER BY created DESC
                 LIMIT :limit
                 OFFSET :offset """

    result = connection.execute(sqlalchemy.text(query), args)
    return [RecommendationFeedbackSubmit(**dict(row)) for row in result.fetchall()]


def get_feedback_count_for_user(connection, user_id: int) -> int:
    """ Get total number of recommendation feedback given by the user

        Args:
            user_id: the row ID of the user in the DB

        Returns:
            The total number of recommendation feedback given by the user
    """
    result = connection.execute(sqlalchemy.text("""
        SELECT count(*) AS count
          FROM recommendation_feedback
         WHERE user_id = :user_id
        """), {
            'user_id': user_id,
        }
    )
    count = int(result.fetchone()["count"])

    return count


def get_feedback_for_multiple_recordings_for_user(connection, user_id: int, recording_list: List[str]):
    """ Get a list of recording feedback given by the user for given recordings

        Args:
            user_id: the row ID of the user in the DB
            recording_list: list of recording_mbid for which feedback records are to be obtained
                            - if record is present then return it
                            - if record is not present then return rating = None

        Returns:
            A list of Feedback objects
    """

    args = {"user_id": user_id, "recording_list": tuple(recording_list)}
    query = """ SELECT user_id,
                       recording_mbid::text,
                       rating,
                       created
                  FROM recommendation_feedback
                 WHERE user_id = :user_id
                   AND recording_mbid
                    IN :recording_list
              ORDER BY created DESC
            """
    result = connection.execute(sqlalchemy.text(query), args)
    return [RecommendationFeedbackSubmit(**dict(row)) for row in result.fetchall()]
