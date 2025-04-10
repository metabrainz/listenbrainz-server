import os.path
import shutil
import tempfile
import zipfile
from datetime import datetime, date, time, timedelta, timezone
from pathlib import Path

import orjson
from brainzutils.mail import send_mail
from dateutil.relativedelta import relativedelta
from flask import current_app, render_template
from sqlalchemy import text

from listenbrainz.db import user as db_user
from listenbrainz.webserver import timescale_connection

BATCH_SIZE = 1000
USER_DATA_EXPORT_AVAILABILITY = timedelta(days=30)  # how long should a user data export be saved for on our servers


def update_export_progress(db_conn, export_id, progress):
    """ Update progress for user data export """
    db_conn.execute(text("""
        UPDATE user_data_export
           SET progress = :progress
         WHERE id = :export_id
    """), {"export_id": export_id, "progress": progress})
    db_conn.commit()


def get_time_ranges_for_listens(min_dt: datetime, max_dt: datetime):
    """ Get year-month sub periods for a given time range. """
    years = []
    for year in range(min_dt.year, max_dt.year + 1):
        if year == min_dt.year:
            start_month = min_dt.month
        else:
            start_month = 1

        if year == max_dt.year:
            end_month = max_dt.month
        else:
            end_month = 12

        months = []
        for month in range(start_month, end_month + 1):
            start_date = date(year, month, 1)
            end_date = start_date + relativedelta(months=1, days=-1)
            months.append({
                "month": month,
                "start": datetime.combine(start_date, time.min, tzinfo=timezone.utc),
                "end": datetime.combine(end_date, time.max, tzinfo=timezone.utc),
            })
        years.append({
            "year": year,
            "months": months
        })

    return years


def export_query_to_jsonl(conn, file_path, query, **kwargs):
    """ Export the given query's data to the given file path in jsonl format. """
    rowcount = 0
    with conn.execute(
        text(query).execution_options(yield_per=BATCH_SIZE),
        kwargs
    ) as result, open(file_path, "w") as file:
        for partition in result.partitions():
            for row in partition:
                file.write(row.line)
                file.write("\n")
                rowcount += 1
    return rowcount


def export_listens_for_time_range(ts_conn, file_path, user_id: int, start_time: datetime, end_time: datetime):
    """ Export user's listens for a given time period. """
    query = """
          WITH selected_listens AS (
                SELECT l.listened_at
                     , l.created as inserted_at
                     , l.data
                     , l.recording_msid
                     , COALESCE((data->'additional_info'->>'recording_mbid')::uuid, user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid) AS recording_mbid
                  FROM listen l
             LEFT JOIN mbid_mapping mm
                    ON l.recording_msid = mm.recording_msid
             LEFT JOIN mbid_manual_mapping user_mm
                    ON l.recording_msid = user_mm.recording_msid
                   AND user_mm.user_id = l.user_id 
             LEFT JOIN mbid_manual_mapping_top other_mm
                    ON l.recording_msid = other_mm.recording_msid
                 WHERE listened_at >= :start_time
                   AND listened_at <= :end_time
                   AND l.user_id = :user_id
          )
                SELECT jsonb_build_object(
                            'listened_at'
                          ,  extract(epoch from listened_at)
                          , 'inserted_at'
                          ,  extract(epoch from inserted_at)
                          , 'track_metadata'
                          , jsonb_set(
                                jsonb_set(data, '{recording_msid}'::text[], to_jsonb(recording_msid::text)),
                                    '{mbid_mapping}'::text[]
                                  , CASE
                                    WHEN mbc.recording_mbid IS NULL
                                    THEN 'null'::jsonb
                                    ELSE 
                                       jsonb_build_object(
                                          'recording_name'
                                        , mbc.recording_data->>'name'
                                        , 'recording_mbid'
                                        , mbc.recording_mbid::text
                                        , 'release_mbid'
                                        , mbc.release_mbid::text
                                        , 'artist_mbids'
                                        , mbc.artist_mbids::TEXT[]
                                        , 'caa_id'
                                        , (mbc.release_data->>'caa_id')::bigint
                                        , 'caa_release_mbid'
                                        , (mbc.release_data->>'caa_release_mbid')::text
                                        , 'artists'
                                        , jsonb_agg(
                                            jsonb_build_object(
                                                'artist_credit_name'
                                              , artist->>'name'
                                              , 'join_phrase'
                                              , artist->>'join_phrase'
                                              , 'artist_mbid'
                                              , mbc.artist_mbids[position]
                                            )
                                            ORDER BY position
                                          )
                                        )
                                    END
                            )
                       )::text as line
                  FROM selected_listens sl
             LEFT JOIN mapping.mb_metadata_cache mbc
                    ON sl.recording_mbid = mbc.recording_mbid
     LEFT JOIN LATERAL jsonb_array_elements(artist_data->'artists') WITH ORDINALITY artists(artist, position)
                    ON TRUE
              GROUP BY sl.listened_at
                     , sl.inserted_at
                     , sl.recording_msid
                     , sl.data
                     , mbc.recording_mbid
                     , recording_data->>'name'
                     , release_mbid
                     , artist_mbids
                     , artist_data->>'name'
                     , recording_data->>'name'
                     , release_data->>'name'
                     , release_data->>'caa_id'
                     , release_data->>'caa_release_mbid'
              ORDER BY listened_at
    """
    return export_query_to_jsonl(ts_conn, file_path, query, user_id=user_id, start_time=start_time, end_time=end_time)


def export_listens_for_user(export_id, db_conn, ts_conn, tmp_dir: str, user_id: int) -> list[str]:
    """ Export user's listens to files organized by year and month in jsonl format. """
    update_export_progress(db_conn, export_id, "Exporting user listens")
    files = []
    min_ts, max_ts = timescale_connection._ts.get_timestamps_for_user(user_id)
    time_ranges = get_time_ranges_for_listens(min_ts, max_ts)

    for time_range in time_ranges:
        year_dir = os.path.join(tmp_dir, "listens", str(time_range["year"]))
        os.makedirs(year_dir, exist_ok=True)
        for period in time_range["months"]:
            period_str = datetime.strftime(period["start"], "%Y-%m-%d") + " " + datetime.strftime(period["end"], "%Y-%m-%d")
            update_export_progress(db_conn, export_id, f"Exporting listens for the period {period_str}")
            file_path = os.path.join(year_dir, f"{period['month']}.jsonl")

            rowcount = export_listens_for_time_range(ts_conn, file_path, user_id, period["start"], period["end"])
            if rowcount > 0:
                files.append(file_path)

    return files


def export_feedback_for_user(export_id, db_conn, tmp_dir: str, user_id: int) -> str | None:
    """ Export user's feedback to a file in jsonl format. """
    update_export_progress(db_conn, export_id, "Exporting user feedback")
    file_path = os.path.join(tmp_dir, "feedback.jsonl")
    query = """
        SELECT jsonb_build_object(
                    'recording_msid'
                  , to_jsonb(recording_msid::text)
                  , 'recording_mbid'
                  , to_jsonb(recording_mbid::text)
                  , 'score'
                  , score
                  , 'created'
                  , extract(epoch from created)::integer
               )::text as line
          FROM recording_feedback
         WHERE user_id = :user_id
      ORDER BY created ASC
    """
    rowcount = export_query_to_jsonl(db_conn, file_path, query, user_id=user_id)
    if rowcount > 0:
        return file_path
    return None


def export_pinned_recordings_for_user(export_id, db_conn, tmp_dir: str, user_id: int) -> str | None:
    """ Export user's pinned recordings to a file in jsonl format. """
    update_export_progress(db_conn, export_id, "Exporting user pinned recordings")
    file_path = os.path.join(tmp_dir, "pinned_recording.jsonl")
    query = """
        SELECT jsonb_build_object(
                    'recording_msid'
                  , to_jsonb(recording_msid::text)
                  , 'recording_mbid'
                  , to_jsonb(recording_mbid::text)
                  , 'blurb_content'
                  , blurb_content
                  , 'pinned_until'
                  , extract(epoch from pinned_until)::integer
                  , 'created'
                  , extract(epoch from created)::integer
               )::text as line
          FROM pinned_recording
         WHERE user_id = :user_id
      ORDER BY created ASC
    """
    rowcount = export_query_to_jsonl(db_conn, file_path, query, user_id=user_id)
    if rowcount > 0:
        return file_path
    return None


def export_info_for_user(export_id, db_conn, tmp_dir, user):
    """ Export user's info to a file in json format. """
    update_export_progress(db_conn, export_id, "Exporting user info")
    file_path = os.path.join(tmp_dir, "user.json")
    with open(file_path, "wb") as file:
        file.write(orjson.dumps({"user_id": user["id"], "username": user["musicbrainz_id"]}))
        file.write(b"\n")
    return file_path


def export_user(db_conn, ts_conn, user_id: int, metadata):
    """ Export all data for the given user in a zip archive """
    user = db_user.get(db_conn, user_id)
    if user is None:
        current_app.logger.error("User with id: %s does not exist, skipping export.", user_id)
        return

    result = db_conn.execute(text("""
        SELECT *
          FROM user_data_export
         WHERE id = :export_id
    """), {"export_id": metadata["export_id"]})
    export = result.first()
    if export is None:
        current_app.logger.error("No export with export_id: %s, skipping.", metadata["export_id"])
        return

    export_id = export.id

    archive_name =  f"listenbrainz_{user.musicbrainz_id}_{int(datetime.now().timestamp())}.zip"
    dest_path = os.path.join(current_app.config["USER_DATA_EXPORT_BASE_DIR"], archive_name)
    os.makedirs(current_app.config["USER_DATA_EXPORT_BASE_DIR"], exist_ok=True)

    db_conn.execute(text("""
         UPDATE user_data_export
            SET
                filename = :filename
              , status = 'in_progress'
              , progress = :progress
          WHERE id = :export_id    
    """), {
        "export_id": export_id,
        "filename": archive_name,
        "progress": "Starting export",
    })
    db_conn.commit()

    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = os.path.join(tmp_dir, archive_name)
        with zipfile.ZipFile(archive_path, "w") as archive:
            all_files = []

            user_file = export_info_for_user(export_id, db_conn, tmp_dir, user)
            all_files.append(user_file)

            listen_files = export_listens_for_user(export_id, db_conn, ts_conn, tmp_dir, user_id)
            all_files.extend(listen_files)

            feedback_file = export_feedback_for_user(export_id, db_conn, tmp_dir, user_id)
            if feedback_file:
                all_files.append(feedback_file)

            pinned_recording_file = export_pinned_recordings_for_user(export_id, db_conn, tmp_dir, user_id)
            if pinned_recording_file:
                all_files.append(pinned_recording_file)

            update_export_progress(db_conn, export_id, "Writing export files")
            for file in all_files:
                archive.write(file, arcname=os.path.relpath(file, tmp_dir))

        update_export_progress(db_conn, export_id, "Finalizing user data export")
        shutil.move(archive_path, dest_path)

    created = datetime.now()
    available_until = created + USER_DATA_EXPORT_AVAILABILITY
    result = db_conn.execute(text("""
        UPDATE user_data_export
           SET progress = :progress
             , available_until = :available_until
             , status = 'completed'
         WHERE id = :export_id
     RETURNING id
    """), {"export_id": export_id, "available_until": available_until, "progress": "Export completed"})
    db_conn.commit()

    if result.first() is None:
        return

    try:
        notify_user_email(db_conn, user_id)
    except Exception as e:
        current_app.logger.error("Failed to notify user: %s", e)


def notify_user_email(db_conn, user_id):
    user = db_user.get(db_conn, user_id, fetch_email=True)
    if user["email"] is None:
        return
    url = current_app.config['SERVER_ROOT_URL'] + '/settings/export/'
    content = render_template('emails/export_completed.txt', username=user["musicbrainz_id"], url=url)
    send_mail(
        subject='ListenBrainz User Data Export',
        text=content,
        recipients=[user["email"]],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )


def cleanup_old_exports(db_conn):
    """ Delete user data exports that have expired or are absent (new export created) from user_data_export table """
    with db_conn.begin():
        db_conn.execute(text("DELETE FROM user_data_export WHERE available_until < NOW()"))
        result = db_conn.execute(text("SELECT filename FROM user_data_export"))
        files_to_keep = {r.filename for r in result.all()}

        # delete exports that are no longer required
        for path in Path(current_app.config["USER_DATA_EXPORT_BASE_DIR"]).iterdir():
            if path.is_file() and path.name not in files_to_keep:
                current_app.logger.info("Removing file: %s", path)
                path.unlink(missing_ok=True)
