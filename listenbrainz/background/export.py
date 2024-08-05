import os.path
import shutil
import tempfile
import zipfile
from datetime import datetime, date, time

from dateutil.relativedelta import relativedelta
from sqlalchemy import text

from listenbrainz.webserver import timescale_connection

BATCH_SIZE = 1000


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
                "start": datetime.combine(start_date, time.min),
                "end": datetime.combine(end_date, time.max)
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


def export_listens_for_time_range(conn, file_path, user_id: int, start_time: datetime, end_time: datetime):
    """ Export user's listens for a given time period. """
    query = """
        SELECT jsonb_build_object(
                    'listened_at'
                  ,  extract(epoch from listened_at)
                  , 'track_metadata'
                  , jsonb_set(data, '{recording_msid}'::text[], to_jsonb(recording_msid::text))
               )::text as line
          FROM listen
         WHERE listened_at >= :start_time
           AND listened_at <= :end_time
           AND user_id = :user_id
      ORDER BY listened_at ASC
    """
    return export_query_to_jsonl(conn, file_path, query, user_id=user_id, start_time=start_time, end_time=end_time)


def export_listens_for_user(ts_conn, tmp_dir: str, user_id: int) -> list[str]:
    """ Export user's listens to files organized by year and month in jsonl format. """
    files = []
    min_ts, max_ts = timescale_connection._ts.get_timestamps_for_user(user_id)
    time_ranges = get_time_ranges_for_listens(min_ts, max_ts)

    for time_range in time_ranges:
        year_dir = os.path.join(tmp_dir, "listens", str(time_range["year"]))
        os.makedirs(year_dir, exist_ok=True)
        for period in time_range["months"]:
            file_path = os.path.join(year_dir, f"{period['month']}.jsonl")

            rowcount = export_listens_for_time_range(ts_conn, file_path, user_id, period["start"], period["end"])
            if rowcount > 0:
                files.append(file_path)

    return files


def export_feedback_for_user(db_conn, tmp_dir: str, user_id: int) -> str | None:
    """ Export user's feedback to a file in jsonl format. """
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
                  , extract(epoch from created)
               )::text as line
          FROM recording_feedback
         WHERE user_id = :user_id
      ORDER BY created ASC
    """
    rowcount = export_query_to_jsonl(db_conn, file_path, query, user_id=user_id)
    if rowcount > 0:
        return file_path
    return None


def export_pinned_recordings_for_user(db_conn, tmp_dir: str, user_id: int) -> str | None:
    """ Export user's pinned recordings to a file in jsonl format. """
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
                  , extract(epoch from pinned_until)
                  , 'created'
                  , extract(epoch from created)
               )::text as line
          FROM pinned_recording
         WHERE user_id = :user_id
      ORDER BY created ASC
    """
    rowcount = export_query_to_jsonl(db_conn, file_path, query, user_id=user_id)
    if rowcount > 0:
        return file_path
    return None


def export_user(db_conn, ts_conn, user_id: int):
    """ Export all data for the given user in a zip archive """
    archive_name = f"export_{user_id}.zip"
    dest_path = os.path.join(archive_name)

    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = os.path.join(tmp_dir, archive_name)
        with zipfile.ZipFile(archive_path, "w") as archive:
            listen_files = export_listens_for_user(ts_conn, tmp_dir, user_id)
            feedback_file = export_feedback_for_user(db_conn, tmp_dir, user_id)
            pinned_recording_file = export_pinned_recordings_for_user(db_conn, tmp_dir, user_id)

            all_files = []
            all_files.extend(listen_files)
            if feedback_file:
                all_files.append(feedback_file)
            if pinned_recording_file:
                all_files.append(pinned_recording_file)

            for file in all_files:
                archive.write(file, arcname=os.path.relpath(file, tmp_dir))

        shutil.move(archive_path, dest_path)
