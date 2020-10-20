import sqlalchemy

from listenbrainz import db
from listenbrainz.db.model.recommendation_feedback import (RecommendationFeedbackSubmit,
                                                           RecommendationFeedbackDelete)
from typing import List


def insert(feedback_submit: RecommendationFeedbackSubmit):
    """ Inserts a feedback record for a user's rated recommendation into the database.
        If the record is already present for the user, the rating is updated to the new
        value passed.

        Args:
            feedback_submit: An object of class RecommendationFeedbackSubmit
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO recommendation_feedback (user_id, recording_mbid, rating)
                 VALUES (:user_id, :recording_mbid, :rating)
            ON CONFLICT (user_id, recording_mbid)
          DO UPDATE SET rating = :rating,
                        created = NOW()
            """), {
                'user_id': feedback_submit.user_id,
                'recording_mbid': feedback_submit.recording_mbid,
                'rating': feedback_submit.rating,
            }
        )


def delete(feedback_delete: RecommendationFeedbackDelete):
    """ Deletes the feedback record for a given recommendation for the user from the database

        Args:
            feedback_delete: An object of class RecommendationFeedbackDelete
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM recommendation_feedback
             WHERE user_id = :user_id
               AND recording_mbid = :recording_mbid
            """), {
                'user_id': feedback_delete.user_id,
                'recording_mbid': feedback_delete.recording_mbid,
            }
        )


def get_feedback_for_user(user_id: int, limit: int, offset: int, rating: str = None) -> List[RecommendationFeedbackSubmit]:
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

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), args)
        return [RecommendationFeedbackSubmit(**dict(row)) for row in result.fetchall()]


def get_feedback_count_for_user(user_id: int) -> int:
    """ Get total number of recommendation feedback given by the user

        Args:
            user_id: the row ID of the user in the DB

        Returns:
            The total number of recommendation feedback given by the user
    """
    with db.engine.connect() as connection:
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
