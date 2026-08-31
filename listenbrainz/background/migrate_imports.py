""" Migrate the files uploaded for user data imports from the upload directory to Garage.

The files users upload to import their listens used to be written to the directory named by
UPLOAD_FOLDER, shared between the webserver and the background tasks container. They are stored
in the Garage bucket named by GARAGE_USER_DATA_IMPORT_BUCKET now, with the name the webserver
generated for the file as the object name.

Only imports that have not run yet still need their file, the importer deletes the file of an
import as soon as it is done with it. So the files of imports that are waiting or in progress are
uploaded, everything else in the directory is a leftover that is left alone (or removed with
--delete-source). Imports that are still pending but whose file exists neither in the bucket nor
on disk cannot be run, so they are marked as failed and the user is asked to upload the file
again. Because that is a destructive and irreversible update, it is skipped unless the directory
actually contained a file of a pending import; pass --mark-missing-failed to do it anyway.

The file_path column holds the full path of the file on disk for imports created before this
migration, it is rewritten to the object name at the end of the run (a run that found no file of
a pending import at all rewrites nothing, its scan cannot be trusted). The importer takes the
basename of file_path either way, so an import queued before this migration ran still works.
"""
import os
from collections import defaultdict
from pathlib import Path

import click
from flask import current_app
from sqlalchemy import text

from listenbrainz.background.listens_importer.storage import PENDING_STATUSES
from listenbrainz.garage import bucket_exists, ensure_bucket, get_garage_client, \
    get_user_data_import_bucket, list_object_names

FILE_MISSING_PROGRESS = "The uploaded file is no longer available, please start the import again."


def get_pending_imports(db_conn) -> dict[str, list[int]]:
    """ Get the import ids of all imports that have not run yet, keyed by the file's object name. """
    result = db_conn.execute(text("""
        SELECT id, file_path
          FROM user_data_import
         WHERE metadata->>'status' = ANY(:statuses)
           AND file_path IS NOT NULL
    """), {"statuses": list(PENDING_STATUSES)})
    imports = defaultdict(list)
    for row in result:
        imports[os.path.basename(row.file_path)].append(row.id)
    return imports


def get_all_import_filenames(db_conn) -> set[str]:
    """ Get the object names of the files of all imports, whatever their status. """
    result = db_conn.execute(text("SELECT file_path FROM user_data_import WHERE file_path IS NOT NULL"))
    return {os.path.basename(row.file_path) for row in result}


def mark_imports_failed(db_conn, import_ids: list[int]):
    """ Mark the given imports as failed so that the user is asked to start a new one. """
    db_conn.execute(text("""
        UPDATE user_data_import
           SET metadata = metadata || jsonb_build_object('status', 'failed', 'progress', :progress)
         WHERE id = ANY(:import_ids)
    """), {"import_ids": import_ids, "progress": FILE_MISSING_PROGRESS})
    db_conn.commit()


def rewrite_file_paths(db_conn) -> int:
    """ Replace the on-disk path of the uploaded file with the object name it is stored under. """
    result = db_conn.execute(text("""
        UPDATE user_data_import
           SET file_path = regexp_replace(file_path, '^.*/', '')
         WHERE file_path LIKE '%/%'
    """))
    db_conn.commit()
    return result.rowcount


def migrate_imports(db_conn, upload_dir: str, delete_source: bool = False, dry_run: bool = False,
                    mark_missing_failed: bool = False):
    """ Upload the files in upload_dir to garage and update the database. """
    source_dir = Path(upload_dir)
    if not source_dir.is_dir():
        raise click.ClickException(f"Upload directory does not exist: {upload_dir}")

    client = get_garage_client()
    bucket = get_user_data_import_bucket()
    if dry_run:
        # the bucket is created by ops in production but may not exist yet, a dry run should
        # still report what it would do instead of erroring out with NoSuchBucket
        bucket_available = bucket_exists(client, bucket)
        if not bucket_available:
            current_app.logger.info("Bucket %s does not exist yet, it would be created", bucket)
    else:
        ensure_bucket(client, bucket)
        bucket_available = True

    pending = get_pending_imports(db_conn)
    known_filenames = get_all_import_filenames(db_conn)
    # files that do not need to be uploaded (again), this run's uploads are added as they happen
    available = set(list_object_names(client, bucket)) if bucket_available else set()
    files = sorted(path for path in source_dir.iterdir() if path.is_file())

    uploaded_count, skipped_count, finished_count, orphan_count = 0, 0, 0, 0
    # files that are safe to delete with --delete-source, and the ones that only look that way
    # because no import exists for them yet
    deletable, orphans = [], []

    for path in files:
        if path.name in pending:
            if path.name in available:
                current_app.logger.info("%s already exists in garage, not uploading it again", path.name)
                skipped_count += 1
            else:
                current_app.logger.info("Uploading %s (%d bytes)", path.name, path.stat().st_size)
                if not dry_run:
                    client.upload_file(str(path), bucket, path.name)
                available.add(path.name)
                uploaded_count += 1
            deletable.append(path)
        elif path.name in known_filenames:
            # the importer deletes the file when it is done, this one was left behind by a crash
            current_app.logger.info("%s belongs to an import that has already run, not migrating it", path.name)
            finished_count += 1
            deletable.append(path)
        else:
            current_app.logger.info("No import exists for %s, not migrating it", path.name)
            orphan_count += 1
            orphans.append(path)

    if delete_source and not dry_run:
        # the imports were read before the upload started, one created since then turns a file
        # that looked like an orphan into the file of a pending import that was never uploaded
        known_now = get_all_import_filenames(db_conn)
        for path in orphans:
            if path.name in known_now:
                current_app.logger.warning(
                    "An import was created for %s while the migration ran, keeping the file."
                    " Run the migration again to upload it.", path.name
                )
            else:
                path.unlink(missing_ok=True)
        for path in deletable:
            path.unlink(missing_ok=True)

    missing = {filename: ids for filename, ids in pending.items() if filename not in available}
    # every pending import looks missing if the wrong directory was passed or the upload volume
    # was not mounted, such a run must not update the table at all
    empty_scan = bool(missing) and uploaded_count + skipped_count == 0 and not mark_missing_failed
    marked_failed = 0
    if missing:
        if empty_scan:
            current_app.logger.warning(
                "%d pending import(s) have no file but no file of a pending import was found in %s"
                " either. Not marking them as failed, check the directory and re-run with"
                " --mark-missing-failed if this is expected.",
                len(missing), upload_dir
            )
        else:
            current_app.logger.info(
                "Marking %d import(s) as failed, their file is missing: %s",
                len(missing), ", ".join(sorted(missing))
            )
            marked_failed = len(missing)
            if not dry_run:
                mark_imports_failed(db_conn, [import_id for ids in missing.values() for import_id in ids])

    rewritten = 0
    if not dry_run and not empty_scan:
        rewritten = rewrite_file_paths(db_conn)

    current_app.logger.info(
        "Migrated %d file(s), %d already in garage, %d of imports that already ran, %d without an import,"
        " %d import(s) marked failed, %d file path(s) rewritten.",
        uploaded_count, skipped_count, finished_count, orphan_count, marked_failed, rewritten
    )
