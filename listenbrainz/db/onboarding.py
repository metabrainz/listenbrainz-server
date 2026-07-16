from typing import Dict

import sqlalchemy
from listenbrainz import db
from listenbrainz.db import couchdb
from listenbrainz.webserver import ts_conn

TOURS = ("setup", "listens", "stats", "social")

# Unlock conditions evaluated for each tour
def _check_unlock_conditions(db_conn, ts_db_conn, user_id: int, tour_id: str) -> bool:
    """Return True if the tour's unlock condition is met."""
    if tour_id == "setup":
        return True

    if tour_id == "listens":
        # Unlock when user has at least one listen
        try:
            result = ts_db_conn.execute(
                sqlalchemy.text(
                    "SELECT 1 FROM listen WHERE user_id = :user_id LIMIT 1"
                ),
                {"user_id": user_id},
            )
            return result.fetchone() is not None
        except Exception:
            return False

    if tour_id == "stats":
        # Unlock when weekly stat type exists for the user.
        REQUIRED_STATS = (
            "listening_activity",
            "artists",
            "release_groups",
            "recordings",
            "daily_activity",
            "artist_map",
        )
        try:
            for stat_type in REQUIRED_STATS:
                prefix = f"{stat_type}_week"
                data = couchdb.fetch_data(prefix, user_id)
                if data is not None:
                    return True
            return False
        except Exception:
            return False

    if tour_id == "social":
        # Unlock when user follows at least one user AND has similar_users data
        follows = db_conn.execute(
            sqlalchemy.text(
                """
                SELECT 1 FROM user_relationship
                 WHERE user_0 = :user_id
                   AND relationship_type = 'follow'
                 LIMIT 1
                """
            ),
            {"user_id": user_id},
        ).fetchone()
        if not follows:
            return False
        similar = db_conn.execute(
            sqlalchemy.text(
                "SELECT 1 FROM recommendation.similar_user WHERE user_id = :user_id LIMIT 1"
            ),
            {"user_id": user_id},
        ).fetchone()
        return similar is not None

    return False


def get_onboarding_state(db_conn, user_id: int) -> Dict:
    """Return onboarding state for all implemented tours."""
    for tour_id in TOURS:
        unlock_default = tour_id == "setup"
        db_conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO user_onboarding_state (user_id, tour_id, status, current_step, unlock_ready)
                VALUES (:user_id, :tour_id, 'not_started', 0, :unlock_ready)
                ON CONFLICT (user_id, tour_id) DO NOTHING
                """
            ),
            {"user_id": user_id, "tour_id": tour_id, "unlock_ready": unlock_default},
        )
    db_conn.commit()

    result = db_conn.execute(
        sqlalchemy.text(
            """
            SELECT tour_id, status, current_step, unlock_ready
              FROM user_onboarding_state
             WHERE user_id = :user_id
               AND tour_id = ANY(:tour_ids)
            """
        ),
        {"user_id": user_id, "tour_ids": list(TOURS)},
    )
    rows = result.mappings().all()
    state = {row["tour_id"]: dict(row) for row in rows}

    # Evaluate unlock conditions for locked tours.
    needs_commit = False
    for tour_id in TOURS:
        tour = state.get(tour_id, {})
        if not tour.get("unlock_ready", False):
            try:
                unlocked = _check_unlock_conditions(db_conn, ts_conn, user_id, tour_id)
            except Exception:
                try:
                    db_conn.rollback()
                except Exception:
                    pass
                unlocked = False

            if unlocked:
                db_conn.execute(
                    sqlalchemy.text(
                        """
                        UPDATE user_onboarding_state
                           SET unlock_ready = TRUE,
                               unlocked_at = NOW(),
                               updated_at = NOW()
                         WHERE user_id = :user_id AND tour_id = :tour_id
                        """
                    ),
                    {"user_id": user_id, "tour_id": tour_id},
                )
                state[tour_id]["unlock_ready"] = True
                needs_commit = True

    if needs_commit:
        db_conn.commit()

    return {
        tour_id: {
            "status": data.get("status", "not_started"),
            "current_step": data.get("current_step", 0),
            "unlock_ready": data.get("unlock_ready", False),
        }
        for tour_id, data in state.items()
    }


def upsert_onboarding_state(
    db_conn,
    user_id: int,
    tour_id: str,
    status: str,
    current_step: int,
) -> None:
    """Update the status and step for a specific tour."""
    if tour_id not in TOURS:
        return
    db_conn.execute(
        sqlalchemy.text(
            """
            INSERT INTO user_onboarding_state (user_id, tour_id, status, current_step, updated_at)
            VALUES (:user_id, :tour_id, :status, :current_step, NOW())
            ON CONFLICT (user_id, tour_id)
            DO UPDATE SET
                status       = EXCLUDED.status,
                current_step = EXCLUDED.current_step,
                updated_at   = NOW()
            """
        ),
        {
            "user_id": user_id,
            "tour_id": tour_id,
            "status": status,
            "current_step": current_step,
        },
    )
    db_conn.commit()


def create_setup_onboarding_row(db_conn, user_id: int) -> None:
    """Seed the setup tour row for a brand new user."""
    db_conn.execute(
        sqlalchemy.text(
            """
            INSERT INTO user_onboarding_state (user_id, tour_id, status, current_step, unlock_ready)
            VALUES (:user_id, 'setup', 'not_started', 0, TRUE)
            ON CONFLICT DO NOTHING
            """
        ),
        {"user_id": user_id},
    )
    db_conn.commit()
