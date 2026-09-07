from sqlalchemy import text


# Specificity score weights for each entity type.
# More specific entities get higher scores.
ENTITY_SPECIFICITY_SCORES = {
    'artist': 1,
    'release_group': 2,
    'release': 3,
    'recording': 4,
}

# Maximum number of recommendations a user can make per day
DAILY_RATE_LIMIT = 10


def compute_specificity_score(source_entity_type, target_entity_type):
    """Compute the specificity score for a recommendation.

    The score is the sum of the source and target entity type weights.
    Range: 2 (artist→artist) to 8 (recording→recording).
    """
    return ENTITY_SPECIFICITY_SCORES[source_entity_type] + ENTITY_SPECIFICITY_SCORES[target_entity_type]


def check_rate_limit(db_conn, user_id):
    """Check how many recommendations the user has made in the last 24 hours.

    Returns the count of recommendations made in the last 24 hours.
    """
    query = """
        SELECT count(*) AS count
          FROM recommendation.entity_recommendation
         WHERE user_id = :user_id
           AND created > NOW() - INTERVAL '24 hours'
    """
    result = db_conn.execute(text(query), {"user_id": user_id})
    return result.first().count


def insert(db_conn, user_id, source_entity_type, source_entity_mbid,
           target_entity_type, target_entity_mbid, blurb=None):
    """Add an entity recommendation.

    Checks rate limit before inserting. On conflict (same user + source + target),
    updates the blurb and specificity score.

    Args:
        db_conn: database connection
        user_id: the row id of the user making the recommendation
        source_entity_type: type of the source entity (artist, release_group, release, recording)
        source_entity_mbid: MusicBrainz ID of the source entity
        target_entity_type: type of the target entity
        target_entity_mbid: MusicBrainz ID of the target entity
        blurb: optional text explanation for the recommendation

    Returns:
        True if inserted successfully

    Raises:
        ValueError: if rate limit exceeded
    """
    current_count = check_rate_limit(db_conn, user_id)
    if current_count >= DAILY_RATE_LIMIT:
        raise ValueError(
            f"Rate limit exceeded. You can only make {DAILY_RATE_LIMIT} recommendations per day. "
            f"You have already made {current_count}."
        )

    specificity_score = compute_specificity_score(source_entity_type, target_entity_type)

    query = """
        INSERT INTO recommendation.entity_recommendation
               (user_id, source_entity_type, source_entity_mbid,
                target_entity_type, target_entity_mbid, specificity_score, blurb)
             VALUES (:user_id, :source_entity_type, :source_entity_mbid,
                     :target_entity_type, :target_entity_mbid, :specificity_score, :blurb)
        ON CONFLICT (user_id, source_entity_type, source_entity_mbid, target_entity_type, target_entity_mbid)
          DO UPDATE SET blurb = EXCLUDED.blurb,
                        specificity_score = EXCLUDED.specificity_score,
                        created = NOW()
    """
    db_conn.execute(text(query), {
        "user_id": user_id,
        "source_entity_type": source_entity_type,
        "source_entity_mbid": source_entity_mbid,
        "target_entity_type": target_entity_type,
        "target_entity_mbid": target_entity_mbid,
        "specificity_score": specificity_score,
        "blurb": blurb,
    })
    db_conn.commit()
    return True


def delete(db_conn, user_id, source_entity_type, source_entity_mbid,
           target_entity_type, target_entity_mbid):
    """Remove an entity recommendation."""
    query = """
        DELETE FROM recommendation.entity_recommendation
              WHERE user_id = :user_id
                AND source_entity_type = :source_entity_type
                AND source_entity_mbid = :source_entity_mbid
                AND target_entity_type = :target_entity_type
                AND target_entity_mbid = :target_entity_mbid
    """
    db_conn.execute(text(query), {
        "user_id": user_id,
        "source_entity_type": source_entity_type,
        "source_entity_mbid": source_entity_mbid,
        "target_entity_type": target_entity_type,
        "target_entity_mbid": target_entity_mbid,
    })
    db_conn.commit()


def get(db_conn, user_id, count, offset):
    """Retrieve entity recommendations made by the specified user.

    Results are ordered by specificity_score descending (most specific first),
    then by creation date descending.
    """
    query = """
        SELECT user_id
             , source_entity_type
             , source_entity_mbid
             , target_entity_type
             , target_entity_mbid
             , specificity_score
             , blurb
             , EXTRACT(epoch FROM created)::int AS created
          FROM recommendation.entity_recommendation
         WHERE user_id = :user_id
      ORDER BY specificity_score DESC, created DESC
         LIMIT :count
        OFFSET :offset
    """
    result = db_conn.execute(text(query), {"user_id": user_id, "count": count, "offset": offset})
    return [
        {
            "source_entity_type": r.source_entity_type,
            "source_entity_mbid": str(r.source_entity_mbid),
            "target_entity_type": r.target_entity_type,
            "target_entity_mbid": str(r.target_entity_mbid),
            "specificity_score": r.specificity_score,
            "blurb": r.blurb,
            "created": r.created,
        }
        for r in result.fetchall()
    ]


def get_total_count(db_conn, user_id):
    """Get the total count of entity recommendations for a given user."""
    query = """
        SELECT count(*) AS count
          FROM recommendation.entity_recommendation
         WHERE user_id = :user_id
    """
    result = db_conn.execute(text(query), {"user_id": user_id})
    return result.first().count
