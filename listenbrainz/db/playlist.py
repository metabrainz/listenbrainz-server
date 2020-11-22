import collections
from typing import List, Optional

import sqlalchemy

from listenbrainz.db.model import playlist as model_playlist
from listenbrainz.db import timescale as ts
from listenbrainz.db import user as db_user


def get_by_mbid(playlist_id: str, load_recordings: bool = True) -> Optional[model_playlist.Playlist]:
    """Get a playlist given its mbid

    Arguments:
        playlist_id: the uuid of a playlist to get
        load_recordings: If true, load the recordings for the playlist too

    Raises:
        ValueError: if playlist_id isn't a valid uuid

    Returns:
        a ``model_playlist.Playlist``, or ``None`` if no such Playlist with the
        given id exists
    """
    query = sqlalchemy.text("""
        SELECT id
             , mbid
             , creator_id
             , name
             , description
             , public
             , created
             , copied_from_id
             , created_for_id
             , algorithm_metadata
          FROM playlist.playlist
         WHERE mbid = :mbid""")
    with ts.engine.connect() as connection:
        result = connection.execute(query, {"mbid": playlist_id})
        obj = result.fetchone()
        if not obj:
            return None
        obj = dict(obj)
        user_id = obj['creator_id']
        user = db_user.get(user_id)
        obj['creator'] = user['musicbrainz_id']
        if load_recordings:
            playlist_map = get_recordings_for_playlists(connection, [obj['id']])
            obj['recordings'] = playlist_map.get(obj['id'], [])
        else:
            obj['recordings'] = []
        return model_playlist.Playlist.parse_obj(obj)


def get_playlists_for_user(user_id: int, include_private: bool = False, load_recordings: bool = False):
    """Get all playlists that a user created

    Arguments:
        user_id: The user to find playlists for
        include_private: If True, include all playlists by a user, including private ones
        load_recordings: If true, load the recordings for the playlist too

    Raises:

    Returns:
        A list of Playlists created by the given user

    """

    params = {"creator_id": user_id}
    where_public = ""
    if not include_private:
        where_public = "AND public = :public"
        params["public"] = True
    query = sqlalchemy.text(f"""
        SELECT id
             , mbid
             , creator_id
             , name
             , description
             , public
             , created
             , copied_from
             , created_for_id
             , algorithm_metadata
          FROM playlist.playlist
         WHERE creator_id = :creator_id
               {where_public}""")

    playlists = []
    with ts.engine.connect() as connection:
        result = connection.execute(query, params)
        user_id_map = {}
        for row in result:
            creator_id = row["creator_id"]
            if creator_id not in user_id_map:
                # TODO: Do this lookup in bulk
                user_id_map[creator_id] = db_user.get(creator_id)
            created_for_id = row["created_for_id"]
            if created_for_id and created_for_id not in user_id_map:
                user_id_map[created_for_id] = db_user.get(created_for_id)
            row = dict(row)
            row["creator"] = user_id_map[creator_id]["musicbrainz_id"]
            if created_for_id:
                row["created_for"] = user_id_map[created_for_id]["musicbrainz_id"]
            row["recordings"] = []
            playlist = model_playlist.Playlist.parse_obj(row)
            playlists.append(playlist)

        if load_recordings:
            playlist_ids = [p.id for p in playlists]
            playlist_recordings = get_recordings_for_playlists(connection, playlist_ids)
            for p in playlists:
                p.recordings = playlist_recordings.get(p.id, [])

    return playlists


def get_playlists_created_for_user(user_id: int, load_recordings: bool = False):
    """Get all playlists that were created for a user by bots

    Arguments:
        user_id
        load_recordings

    Raises:

    Returns:

    """

    query = sqlalchemy.text("""
        SELECT id
             , mbid
             , creator_id
             , name
             , description
             , public
             , created
             , copied_from
             , created_for_id
             , algorithm_metadata
          FROM playlist.playlist
         WHERE created_for_id = :created_for_id""")

    # TODO: This is almost exactly the same as get_playlists_for_user
    playlists = []
    with ts.engine.connect() as connection:
        result = connection.execute(query, {"created_for_id": user_id})
        user_id_map = {}
        for row in result:
            creator_id = row["creator_id"]
            if creator_id not in user_id_map:
                # TODO: Do this lookup in bulk
                user_id_map[creator_id] = db_user.get(creator_id)
            created_for_id = row["created_for_id"]
            if created_for_id and created_for_id not in user_id_map:
                user_id_map[created_for_id] = db_user.get(created_for_id)
            row = dict(row)
            row["creator"] = user_id_map[creator_id]["musicbrainz_id"]
            if created_for_id:
                row["created_for"] = user_id_map[created_for_id]["musicbrainz_id"]
            row["recordings"] = []
            playlist = model_playlist.Playlist.parse_obj(row)
            playlists.append(playlist)

        if load_recordings:
            playlist_ids = [p.id for p in playlists]
            playlist_recordings = get_recordings_for_playlists(connection, playlist_ids)
            for p in playlists:
                p.recordings = playlist_recordings.get(p.id, [])

    return playlists


def get_recordings_for_playlists(connection, playlist_ids: List[int]):
    """"""

    query = sqlalchemy.text("""
        SELECT id
             , playlist_id
             , position
             , mbid
             , added_by_id
             , created
          FROM playlist.playlist_recording
         WHERE playlist_id IN :playlist_ids
      ORDER BY playlist_id, position
    """)
    result = connection.execute(query, {"playlist_ids": tuple(playlist_ids)})
    user_id_map = {}
    playlist_recordings_map = collections.defaultdict(list)
    for row in result:
        added_by_id = row["added_by_id"]
        if added_by_id not in user_id_map:
            # TODO: Do this lookup in bulk
            user_id_map[added_by_id] = db_user.get(added_by_id)
        row = dict(row)
        row["added_by"] = user_id_map[added_by_id]["musicbrainz_id"]
        playlist_recording = model_playlist.PlaylistRecording.parse_obj(row)
        playlist_recordings_map[playlist_recording.playlist_id].append(playlist_recording)
    for playlist_id in playlist_ids:
        if playlist_id not in playlist_recordings_map:
            playlist_recordings_map[playlist_id] = []
    return dict(playlist_recordings_map)


def create(playlist: model_playlist.WritablePlaylist) -> model_playlist.Playlist:
    """Create a playlist

    Arguments:
        playlist: A playlist to add

    Raises:
        InvalidUser: if ``playlist.creator_id`` isn't a valid listenbrainz user id,
          or if ``playlist.created_for_id`` is set and isn't a valid listenbrainz user id

    Returns:
        a Playlist, representing the playlist that was inserted, with the id, mbid, and created date added.

    """
    # TODO: These two gets should be done in a single query
    creator = db_user.get(playlist.creator_id)
    if creator is None:
        raise Exception("TODO: Custom exception")
    if playlist.created_for_id:
        created_for = db_user.get(playlist.created_for_id)
        if created_for is None:
            raise Exception("TODO: Custom exception")
    query = sqlalchemy.text("""
        INSERT INTO playlist.playlist (creator_id
                                     , name
                                     , description
                                     , public
                                     , copied_from_id
                                     , created_for_id
                                     , algorithm_metadata)
                               VALUES (:creator_id
                                     , :name
                                     , :description
                                     , :public
                                     , :copied_from_id
                                     , :created_for_id
                                     , :algorithm_metadata)
                             RETURNING id, mbid, created
    """)
    fields = playlist.dict(include={'creator_id', 'name', 'description', 'public',
                                    'copied_from_id', 'created_for_id', 'algorithm_metadata'})
    with ts.engine.connect() as connection:
        result = connection.execute(query, fields)
        row = dict(result.fetchone())
        playlist.id = row['id']
        playlist.mbid = row['mbid']
        playlist.created = row['created']
        playlist.creator = creator['musicbrainz_id']
        playlist.recordings = insert_recordings(connection, playlist.id, playlist.recordings, 0)
        return model_playlist.Playlist.parse_obj(playlist.dict())


def update_playlist(playlist: model_playlist.Playlist):
    """Update playlist metadata (Name, description, public flag)

    Arguments:

    """

    query = sqlalchemy.text("""
        UPDATE playlist.playlist
           SET name = :name
             , description = :description
             , public = :public
         WHERE id = :id
    """)
    with ts.engine.connect() as connection:
        params = playlist.dict(include={'id', 'name', 'description', 'public'})
        connection.execute(query, params)
        return playlist


def copy_playlist(playlist: model_playlist.Playlist, creator_id: int):
    newplaylist = playlist.copy()
    newplaylist.creator_id = creator_id
    newplaylist.copied_from_id = playlist.id

    return create(newplaylist)


def delete_playlist(playlist: model_playlist.Playlist):
    """Delete a playlist.

    Arguments:
        playlist: The playlist to delete

    Returns:
        True if the playlist was deleted, False if no such playlist with the given mbid exists
    """
    return delete_playlist_by_mbid(playlist.mbid)


def delete_playlist_by_mbid(playlist_mbid: str):
    """Delete a playlist given an mbid.

    Arguments:
        playlist_mbid: The mbid of the playlist to delete

    Returns:
        True if the playlist was deleted, False if no such playlist with the given mbid exists
    """
    query = sqlalchemy.text("""
        DELETE FROM playlist.playlist
              WHERE playlist.mbid = :playlist_mbid
    """)
    with ts.engine.connect() as connection:
        result = connection.execute(query, {"playlist_mbid": playlist_mbid})
        return result.rowcount == 1


def insert_recordings(connection, playlist_id: int, recordings: List[model_playlist.WritablePlaylistRecording],
                      starting_position: int):
    """Insert recordings to an existing playlist. The position field will be computed based on the order
    of the provided recordings.

    Arguments:
        connection: an open database connection
        playlist_id: the playlist id to add the recordings to
        recordings: a list of recordings to add
        starting_position: The position number to set in the first recording. The first recording in a playlist is position 0
    """
    for position, recording in enumerate(recordings, starting_position):
        recording.playlist_id = playlist_id
        recording.position = position

    query = sqlalchemy.text("""
        INSERT INTO playlist.playlist_recording (playlist_id, position, mbid, added_by_id)
                                         VALUES (:playlist_id, :position, :mbid, :added_by_id)
                                      RETURNING id, created""")
    return_recordings = []
    user_id_map = {}
    for recording in recordings:
        result = connection.execute(query, recording.dict(include={'playlist_id', 'position', 'mbid', 'added_by_id'}))
        if recording.added_by_id not in user_id_map:
            # TODO: Do this lookup in bulk
            user_id_map[recording.added_by_id] = db_user.get(recording.added_by_id)
        row = result.fetchone()
        recording.id = row['id']
        recording.created = row['created']
        recording.added_by = user_id_map[recording.added_by_id]["musicbrainz_id"]
        return_recordings.append(model_playlist.PlaylistRecording.parse_obj(recording.dict()))
    return return_recordings


def delete_recordings_from_playlist(playlist: model_playlist.Playlist, remove_from: int, remove_count: int):
    """Delete recordings from a playlist. If the remove_from + remove_count is more than the number
    of items in the playlist, silently remove as many as possible

    Arguments:
        playlist: The playlist to remove recordings from
        remove_from: The position to remove from, 0 indexed
        remove_count: The number of items to remove

    Raises:
        ValueError: if ``remove_from`` is less than 0, or greater than the number of recordings in the playlist
        ValueError: if ``remove_count`` is less than or equal to 0

    """
    # If recordings are at the end of the list, just remove them

    # If in the middle, find where they are:
    #   [existing] | [to-remove] | [trailing]
    # Items in trailing need to be renumbered starting from

    # If at the beginning, this is a special case of in the middle
    # TODO: these queries assume that the the passed in playlist is up to date, it should verify
    #   in case it's changed

    if remove_count < 1:
        raise ValueError("Need to ask to remove at least one recording")
    if remove_from < 0:
        raise ValueError("Cannot remove from negative index")
    if remove_from >= len(playlist.recordings):
        raise ValueError("Cannot remove item past the end of the list of recordings")

    delete = sqlalchemy.text("""
        DELETE FROM playlist.playlist_recording
          WHERE playlist_id = :playlist_id
            AND position >= :position_start
            AND position < :position_end
    """)
    reorder = sqlalchemy.text("""
        UPDATE playlist.playlist_recording
           SET position = position + :offset
         WHERE playlist_id = :playlist_id
           AND position >= :position
    """)
    with ts.engine.connect() as connection:
        delete_params = {"playlist_id": playlist.id,
                         "position_start": remove_from,
                         "position_end": remove_from+remove_count}
        connection.execute(delete, delete_params)
        if remove_from + remove_count < len(playlist.recordings):
            reorder_params = {"playlist_id": playlist.id,
                              "position": remove_from + remove_count,
                              "offset": -1 * remove_count}
            connection.execute(reorder, reorder_params)


def add_recordings_to_playlist(playlist: model_playlist.Playlist,
                               recordings: List[model_playlist.WritablePlaylistRecording],
                               position: int = None):
    """Add some recordings to a playlist at a given position

    Recording positions are counted from 0, and recordings are added at the given position. If the playlist
    has other recordings at this position, they will be moved

    Arguments:
        playlist: A Playlist to append to. Must be loaded with ``get_by_id`` and have and id and recordings set
        recordings: A list of recordings to add
        position: The position in the existing playlist after which to add the recordings. If ``None`` or
           the position is greater than the number of recordings currently in the playlist, append them.

    Returns:
        The provided playlist with the recordings added
    """

    # TODO: Need to check if there are actually recordings in this playlist that aren't declared
    #   - can we just check if there's an exception on insert?
    # TODO: Need unique key on (playlist_id, position) on playlist_recording
    # TODO: This is the same reorder method as delete
    reorder = sqlalchemy.text("""
        UPDATE playlist.playlist_recording
           SET position = position + :offset
         WHERE playlist_id = :playlist_id
           AND position >= :position
    """)
    if position is None:
        position = len(playlist.recordings)
    with ts.engine.connect() as connection:
        if position < len(playlist.recordings):
            reorder_params = {"playlist_id": playlist.id,
                              "offset": len(recordings),
                              "position": position}
            connection.execute(reorder, reorder_params)
        recordings = insert_recordings(connection, playlist.id, recordings, position)
        playlist.recordings = playlist.recordings[0:position] + recordings + playlist.recordings[position:]
        return playlist


def move_recordings(playlist: model_playlist.Playlist, position_from: int, position_to: int, count: int):
    # TODO: This must be done in a single transaction
    removed = playlist.recordings[position_from:position_from+count]
    delete_recordings_from_playlist(playlist, position_from, count)
    add_recordings_to_playlist(playlist, removed, position_to)


def update(playlist: model_playlist.Playlist) -> model_playlist.Playlist:
    if not playlist.id:
        raise ValueError("needs an id")
    pass


