from hashlib import sha256
import logging
import copy
import time
import json
import os
import db
import db.exceptions

def submit_low_level_data(mbid, data):
    """Function for submitting low-level data.

    Args:
        mbid: MusicBrainz ID of the recording that corresponds to the data
            that is being submitted.
        data: Low-level data about the recording.
    """
    mbid = str(mbid)
    data = clean_metadata(data)

    try:
        # If the user submitted a trackid key, rewrite to recording_id
        if "musicbrainz_trackid" in data['metadata']['tags']:
            val = data['metadata']['tags']["musicbrainz_trackid"]
            del data['metadata']['tags']["musicbrainz_trackid"]
            data['metadata']['tags']["musicbrainz_recordingid"] = val

        if data['metadata']['audio_properties']['lossless']:
            data['metadata']['audio_properties']['lossless'] = True
        else:
            data['metadata']['audio_properties']['lossless'] = False

    except KeyError:
        pass

    missing_key = sanity_check_data(data)
    if missing_key is not None:
        raise db.exceptions.BadDataException(
            "Key '%s' was not found in submitted data." %
            ' : '.join(missing_key)
        )

    # Ensure the MBID form the URL matches the recording_id from the POST data
    if data['metadata']['tags']["musicbrainz_recordingid"][0].lower() != mbid.lower():
        raise db.exceptions.BadDataException(
            "The musicbrainz_trackid/musicbrainz_recordingid in "
            "the submitted data does not match the MBID that is "
            "part of this resource URL."
        )

    # The data looks good, lets see about saving it
    is_lossless_submit = data['metadata']['audio_properties']['lossless']
    build_sha1 = data['metadata']['version']['essentia_build_sha']
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json.encode("utf-8")).hexdigest()

    with db.create_cursor() as cursor:
        # Checking to see if we already have this data
        cursor.execute("SELECT data_sha256 FROM lowlevel WHERE mbid = %s", (mbid, ))

        # if we don't have this data already, add it
        sha_values = [v[0] for v in cursor.fetchall()]

        if data_sha256 not in sha_values:
            logging.info("Saved %s" % mbid)
            cursor.execute(
                "INSERT INTO lowlevel (mbid, build_sha1, data_sha256, lossless, data)"
                "VALUES (%s, %s, %s, %s, %s)",
                (mbid, build_sha1, data_sha256, is_lossless_submit, data_json)
            )
            db.commit()

        logging.info("Already have %s" % data_sha256)


def load_low_level(mbid, offset=0):
    """Load low-level data for a given MBID."""
    with db.create_cursor() as cursor:
        cursor.execute(
            "SELECT data::text "
            "FROM lowlevel "
            "WHERE mbid = %s "
            "ORDER BY submitted "
            "OFFSET %s",
            (str(mbid), offset)
        )
        if not cursor.rowcount:
            raise db.exceptions.NoDataFoundException

        row = cursor.fetchone()
        return row[0]

def count_lowlevel(mbid):
    """Count number of stored low-level submissions for a specified MBID."""
    with db.create_cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM lowlevel WHERE mbid = %s",
            (str(mbid),)
        )
        return cursor.fetchone()[0]
