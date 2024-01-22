from datetime import datetime, timedelta

from sqlalchemy import text
from troi.patches.periodic_jams import WEEKLY_JAMS_DESCRIPTION, WEEKLY_EXPLORATION_DESCRIPTION

from listenbrainz import db
from listenbrainz.troi.spark import batch_process_playlists, remove_old_playlists, get_user_details

PERIODIC_PLAYLIST_LIFESPAN = 2


def get_users_for_weekly_playlists(create_all):
    """ Retrieve the users who had their midnight in their timezone less than 59 minutes ago and
        where its monday currently and generate the weekly playlists for them.
    """
    timezone_filter = """
        WHERE EXTRACT(HOUR from NOW() AT TIME ZONE COALESCE(us.timezone_name, 'GMT')) = 0
          AND EXTRACT(DOW from NOW() AT TIME ZONE COALESCE(us.timezone_name, 'GMT')) = 1
    """
    query = """
        SELECT "user".id as user_id
             , to_char(NOW() AT TIME ZONE COALESCE(us.timezone_name, 'GMT'), 'YYYY-MM-DD Dy') AS jam_date
          FROM "user"
     LEFT JOIN user_setting us
            ON us.user_id = "user".id
    """
    if not create_all:
        query += " " + timezone_filter
    with db.engine.connect() as connection:
        result = connection.execute(text(query))
        return [dict(r) for r in result.mappings()]


def exclude_playlists_from_deleted_users(slug, jam_name, description, all_playlists):
    """ Remove playlists for users who have deleted their accounts. Also, add more metadata to remaining playlists """
    user_ids = [p["user_id"] for p in all_playlists]
    user_details = get_user_details(slug, user_ids)

    # after removing playlists for users who have been deleted but their
    # data has completely not been removed from spark cluster yet
    playlists = []
    playlists_to_export = []
    for playlist in all_playlists:
        user_id = playlist["user_id"]
        if user_id not in user_details:
            continue

        user = user_details[user_id]
        playlist["name"] = f"{jam_name} for {user['username']}, week of {playlist['jam_date']}"
        playlist["description"] = description
        playlist["existing_url"] = user["existing_url"]
        playlist["additional_metadata"] = {
            "algorithm_metadata": {
                "source_patch": slug
            },
            "expires_at": (datetime.utcnow() + timedelta(weeks=PERIODIC_PLAYLIST_LIFESPAN)).isoformat()
        }

        playlists.append(playlist)
        if user["export_to_spotify"]:
            playlists_to_export.append(playlist)

    return playlists, playlists_to_export


def process_weekly_playlists(slug, playlists):
    """ Insert the playlists generated in batch by spark """
    if slug == "weekly-jams":
        jam_name = "Weekly Jams"
        description = WEEKLY_JAMS_DESCRIPTION
    elif slug == "weekly-exploration":
        jam_name = "Weekly Exploration"
        description = WEEKLY_EXPLORATION_DESCRIPTION
    else:
        return

    all_playlists, playlists_to_export = exclude_playlists_from_deleted_users(slug, jam_name, description, playlists)
    batch_process_playlists(all_playlists, playlists_to_export)


def process_weekly_playlists_end(slug):
    """ Once bulk generated playlists have been inserted in Spark, remove all but the
        two latest playlists of that slug for all users. """
    remove_old_playlists(slug, PERIODIC_PLAYLIST_LIFESPAN)
