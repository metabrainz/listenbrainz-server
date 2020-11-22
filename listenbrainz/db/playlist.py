import collections
from typing import List, Optional

import sqlalchemy

from listenbrainz.db.model import playlist as model_playlist
from listenbrainz.db import timescale as ts
from listenbrainz.db import user as db_user


def get_by_id(playlist_id: str, load_recordings: bool = True) -> Optional[model_playlist.Playlist]:
    """Get a playlist

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
             , copied_from
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
                                     , copied_from
                                     , created_for_id
                                     , algorithm_metadata)
                               VALUES (:creator_id
                                     , :name
                                     , :description
                                     , :public
                                     , :copied_from
                                     , :created_for_id
                                     , :algorithm_metadata)
                             RETURNING id, mbid, created
    """)
    fields = playlist.dict(include={'creator_id', 'name', 'description', 'public',
                                    'copied_from', 'created_for_id', 'algorithm_metadata'})
    with ts.engine.connect() as connection:
        result = connection.execute(query, fields)
        row = dict(result.fetchone())
        playlist.id = row['id']
        playlist.mbid = row['mbid']
        playlist.created = row['created']
        playlist.creator = creator['musicbrainz_id']
        playlist.recordings = insert_recordings(connection, playlist.id, playlist.recordings, 1)
        return model_playlist.Playlist.parse_obj(playlist.dict())


def insert_recordings(connection, playlist_id: int, recordings: List[model_playlist.WritablePlaylistRecording],
                      starting_position: int):
    """Insert recordings to an existing playlist. The position field will be computed based on the order
    of the provided recordings.

    Arguments:
        connection: an open database connection
        playlist_id: the playlist id to add the recordings to
        recordings: a list of recordings to add
        starting_position: The position number to set in the first recording.
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


def add_recordings_to_playlist(playlist: model_playlist.Playlist,
                               recordings: List[model_playlist.WritablePlaylistRecording],
                               position: int = None):
    """Add some recordings to a playlist at a given position

    Recording positions are counted from 1, and recordings are added after the given position.
    A position of 0 has the effect of adding a recording before the first recording in the playlist.

    Arguments:
        playlist: A Playlist to append to. Must be loaded with ``get_by_id`` and have and id and recordings set
        recordings: A list of recordings to add
        position: The position in the existing playlist after which to add the recordings. If ``None`` or
           the position is greater than the number of recordings currently in the playlist, append them.

    Raises:
        ValueError: If you try and insert recordings into the middle of an existing playlist

    Returns:
        The provided playlist with the recordings added
    """

    if position and position < len(playlist.recordings):
        raise ValueError("Cannot insert recordings yet")
    # TODO: Check if this is actually the value of playlist.recordings[-1].position
    starting_position = len(playlist.recordings) + 1
    # TODO: Need to check if there are actually recordings in this playlist that aren't declared
    #   - can we just check if there's an exception on insert?
    # TODO: Need unique key on (playlist_id, position) on playlist_recording
    with ts.engine.connect() as connection:
        recordings = insert_recordings(connection, playlist.id, recordings, starting_position)
        playlist.recordings.extend(recordings)
        return playlist


def update(playlist: model_playlist.Playlist) -> model_playlist.Playlist:
    if not playlist.id:
        raise ValueError("needs an id")
    pass


