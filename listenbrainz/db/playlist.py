from typing import List, Optional

import sqlalchemy

from listenbrainz.db.model import playlist as model_playlist
from listenbrainz.db import timescale as ts
from listenbrainz.db import user as db_user


def get_by_id(playlist_id: str, load_recordings: bool = True) -> Optional[model_playlist.Playlist]:
    """Get a playlist

    Arguments:
        playlist_id: the uuid of a playlist to get

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
        #if load_recordings:
        #    obj['recordings'] = get_recordings_for_playlists([obj['id']])
        #else:
        obj['recordings'] = []
        return model_playlist.Playlist.parse_obj(obj)


def get_playlists_for_user(user_id: int, include_private: bool = False, include_recordings: bool = False):
    """Get all playlists that a user created

    Arguments:
        user_id
        include_private
        include_recordings

    Raises:

    Returns:

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
    with ts.engine.connect() as connection:
        result = connection.execute(query, params)
        # TODO: Finish


def get_playlists_created_for_user(user_id: int, include_recordings: bool = False):
    """Get all playlists that were created for a user

    Arguments:
        user_id
        include_recordings

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
    with ts.engine.connect() as connection:
        result = connection.execute(query, {"created_for_id": user_id})
        # TODO: Finish


def get_recordings_for_playlists(playlist_ids: List[int]):
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
    with ts.engine.connect() as connection:
        result = connection.execute(query, {"playlist_ids": tuple(playlist_ids)})
        return [r for r in result]
        # TODO: Return objects, get usernames


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
    # TODO: This should be done in a single query
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
        playlist.recordings = insert_recordings(connection, playlist.id, playlist.recordings)
        return model_playlist.Playlist.parse_obj(playlist.dict())


def insert_recordings(connection, playlist_id: int, recordings: List[model_playlist.WritablePlaylistRecording]):
    """Insert recordings to an existing playlist. The position field will be computed based on the order
    of the provided recordings.

    Arguments:
        connection: an open database connection
        playlist_id: the playlist id to add the recordings to
        recordings: a list of recordings
    """
    for position, recording in enumerate(recordings, 1):
        recording.playlist_id = playlist_id
        recording.position = position

    query = sqlalchemy.text("""
        INSERT INTO playlist.playlist_recording (playlist_id, position, mbid, added_by_id)
                                         VALUES (:playlist_id, :position, :mbid, :added_by_id)
                                      RETURNING id, created""")
    return_recordings = []
    for recording in recordings:
        result = connection.execute(query, recording.dict(include={'playlist_id', 'position', 'mbid', 'added_by_id'}))
        row = result.fetchone()
        recording.id = row['id']
        recording.created = row['created']
        return_recordings.append(model_playlist.PlaylistRecording.parse_obj(recording.dict()))
    return return_recordings


def update(playlist: model_playlist.Playlist) -> model_playlist.Playlist:
    if not playlist.id:
        raise ValueError("needs an id")
    pass


