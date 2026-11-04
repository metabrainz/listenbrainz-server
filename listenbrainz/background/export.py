import os.path
import tempfile
import zipfile
from datetime import datetime, date, time, timedelta, timezone

import orjson
from brainzutils.mail import send_mail
from dateutil.relativedelta import relativedelta
from flask import current_app, render_template
from sqlalchemy import text

from listenbrainz.db import listens as listens_db, user as db_user
from listenbrainz.garage import delete_objects, ensure_bucket, get_garage_client, \
    get_user_data_export_bucket, list_object_names
from listenbrainz.listenstore.timescale_listenstore import LISTEN_COLUMNS_QUERY
from listenbrainz.webserver import timescale_connection

BATCH_SIZE = 1000
EXPORT_FAILED_PROGRESS = "Export failed, please try again."
USER_DATA_EXPORT_AVAILABILITY = timedelta(days=30)  # how long should a user data export be saved for on our servers


def update_export_progress(db_conn, export_id, progress):
    """ Update progress for user data export """
    db_conn.execute(text("""
        UPDATE user_data_export
           SET progress = :progress
         WHERE id = :export_id
    """), {"export_id": export_id, "progress": progress})
    db_conn.commit()


def mark_export_failed(db_conn, export_id):
    """ Mark the given export as failed.

    An export that is left in progress blocks the user from requesting a new one forever
    because of the user_data_export_deduplicate_waiting_idx unique index, so any failure
    must be recorded in the export's status.
    """
    # the failure may have left the connection in an aborted transaction
    db_conn.rollback()
    db_conn.execute(text("""
        UPDATE user_data_export
           SET status = 'failed'
             , progress = :progress
         WHERE id = :export_id
    """), {"export_id": export_id, "progress": EXPORT_FAILED_PROGRESS})
    db_conn.commit()


def get_time_ranges_for_listens(min_dt: datetime, max_dt: datetime):
    """ Get year-month sub periods for a given time range. """
    if min_dt > max_dt:
        return []
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
                "start": max(min_dt, datetime.combine(start_date, time.min, tzinfo=timezone.utc)),
                "end": min(max_dt, datetime.combine(end_date, time.max, tzinfo=timezone.utc)),
            })
        years.append({
            "year": year,
            "months": months
        })

    return years


def export_query_to_jsonl(conn, file_path, query, **kwargs):
    """ Export the given query's data to the given file path in jsonl format.

    Args:
        conn: database connection
        file_path: path to write the JSONL file
        query: SQL query whose rows must have a text `line` column
        **kwargs: bind parameters forwarded to conn.execute
    """
    rowcount = 0
    with conn.execute(
        text(query).execution_options(yield_per=BATCH_SIZE),
        kwargs
    ) as result, open(file_path, "w", encoding="utf-8") as file:
        for partition in result.partitions():
            for row in partition:
                file.write(row.line)
                file.write("\n")
                rowcount += 1
    return rowcount


def _mbid_mapping_for_export(meta):
    """ Build the exported mbid_mapping of a listen, None if its recording is not in the metadata cache. """
    if meta is None or not meta.has_metadata:
        return None
    artist_mbids = meta.artist_mbids or []
    return {
        "recording_name": meta.recording_name,
        "recording_mbid": str(meta.recording_mbid),
        "release_mbid": str(meta.release_mbid) if meta.release_mbid else None,
        "artist_mbids": artist_mbids,
        "caa_id": meta.caa_id,
        "caa_release_mbid": meta.caa_release_mbid,
        "artists": [
            {
                "artist_credit_name": name,
                "join_phrase": join_phrase,
                "artist_mbid": artist_mbids[idx] if idx < len(artist_mbids) else None,
            }
            for idx, (name, join_phrase) in enumerate(zip(meta.ac_names, meta.ac_join_phrases))
            if name is not None
        ],
    }


def export_listens_for_time_range(listens_conn, file_path, user_id: int, start_time: datetime, end_time: datetime):
    """ Export user's listens for a given time period.

    Listens are streamed from the listens DB, which serves all listen reads and is where deletions
    happen. Mapping metadata is resolved for each batch of listens on listens_conn, a second
    connection to the listens DB, because the streaming connection is busy with the listens query.
    """
    query = LISTEN_COLUMNS_QUERY + """
          FROM listen
         WHERE user_id = :user_id
           AND listened_at >= :start_time
           AND listened_at <= :end_time
      ORDER BY listened_at
    """
    rowcount = 0
    with listens_db.engine.connect() as connection, connection.execute(
        text(query).execution_options(yield_per=BATCH_SIZE),
        {"user_id": user_id, "start_time": start_time, "end_time": end_time}
    ) as result, open(file_path, "wb") as file:
        for partition in result.partitions():
            metadata = timescale_connection._ts._fetch_mapping_metadata(partition, listens_conn)
            for row in partition:
                meta = metadata.get((row.user_id, row.recording_msid, row.submitted_mbid))
                track_metadata = row.data
                track_metadata["mbid_mapping"] = _mbid_mapping_for_export(meta)
                file.write(orjson.dumps({
                    "inserted_at": round(row.created.timestamp()),
                    "listened_at": row.listened_at.timestamp(),
                    "recording_msid": row.recording_msid,
                    "track_metadata": track_metadata,
                }))
                file.write(b"\n")
                rowcount += 1
    return rowcount


def export_listens_for_user(export_id, db_conn, listens_conn, tmp_dir: str, user_id: int,
                            start_time: datetime | None = None, end_time: datetime | None = None) -> list[str]:
    """ Export user's listens to files organized by year and month in jsonl format. """
    update_export_progress(db_conn, export_id, "Exporting user listens")
    files = []
    first_listen, last_listen = timescale_connection._ts.get_timestamps_for_user(user_id)
    min_ts = max(start_time, first_listen) if start_time is not None else first_listen
    max_ts = min(end_time, last_listen) if end_time is not None else last_listen
    time_ranges = get_time_ranges_for_listens(min_ts, max_ts)

    for time_range in time_ranges:
        year_dir = os.path.join(tmp_dir, "listens", str(time_range["year"]))
        os.makedirs(year_dir, exist_ok=True)
        for period in time_range["months"]:
            period_str = datetime.strftime(period["start"], "%Y-%m-%d") + " " + datetime.strftime(period["end"], "%Y-%m-%d")
            update_export_progress(db_conn, export_id, f"Exporting listens for the period {period_str}")
            file_path = os.path.join(year_dir, f"{period['month']}.jsonl")

            rowcount = export_listens_for_time_range(listens_conn, file_path, user_id, period["start"], period["end"])
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


def export_user(db_conn, listens_conn, user_id: int, metadata):
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
    try:
        client = get_garage_client()
        bucket = get_user_data_export_bucket()
        ensure_bucket(client, bucket)

        archive_name = f"listenbrainz_{user.musicbrainz_id}_{int(datetime.now().timestamp())}.zip"

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
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                all_files = []

                user_file = export_info_for_user(export_id, db_conn, tmp_dir, user)
                all_files.append(user_file)

                start_time = metadata.get("start_time")
                end_time = metadata.get("end_time")
                listen_files = export_listens_for_user(
                    export_id, db_conn, listens_conn, tmp_dir, user_id,
                    start_time=datetime.fromtimestamp(start_time, timezone.utc) if start_time is not None else None,
                    end_time=datetime.fromtimestamp(end_time, timezone.utc) if end_time is not None else None,
                )
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
            client.upload_file(archive_path, bucket, archive_name, ExtraArgs={"ContentType": "application/zip"})

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
    except Exception:
        mark_export_failed(db_conn, export_id)
        raise

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
        files_to_keep = {r.filename for r in result.all() if r.filename is not None}

    client = get_garage_client()
    bucket = get_user_data_export_bucket()
    ensure_bucket(client, bucket)

    # Delete exports that are no longer required
    objects_to_delete = []
    for object_name in list_object_names(client, bucket):
        if object_name not in files_to_keep:
            current_app.logger.info("Removing export: %s", object_name)
            objects_to_delete.append(object_name)

    for error in delete_objects(client, bucket, objects_to_delete):
        current_app.logger.error("Failed to remove export %s: %s", error.get("Key"), error.get("Message"))
