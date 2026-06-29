from markupsafe import Markup
import sqlalchemy


def generate_username_link(user_name):
    return Markup(f"""<a href="https://listenbrainz.org/user/{user_name}">{user_name}</a>""")


def set_users_paused(db_conn, user_ids, is_paused):
    user_ids = [int(user_id) for user_id in user_ids]
    return _set_users_paused(db_conn, ":user_ids", {"user_ids": tuple(user_ids)}, is_paused)


def set_reported_users_paused(db_conn, report_ids, is_paused):
    report_ids = [int(report_id) for report_id in report_ids]
    return _set_users_paused(
        db_conn,
        """
            (SELECT DISTINCT reported_user_id
               FROM reported_users
              WHERE id IN :report_ids)
        """,
        {"report_ids": tuple(report_ids)},
        is_paused,
    )


def _set_users_paused(db_conn, user_ids_expression, params, is_paused):
    if not any(params.values()):
        return []

    query = sqlalchemy.text(f"""
        UPDATE "user"
           SET is_paused = :is_paused
         WHERE "user".id IN {user_ids_expression}
     RETURNING "user".musicbrainz_id
    """)
    result = db_conn.execute(query, {
        **params,
        "is_paused": is_paused,
    })
    users = [row.musicbrainz_id for row in result.fetchall()]
    db_conn.commit()
    return users
