import collections
import datetime
from typing import List, Optional

import sqlalchemy
import ujson

from listenbrainz.db.model import playlist as model_playlist
from listenbrainz.db import timescale as ts
from listenbrainz.db import user as db_user


TROI_BOT_USER_ID = 12939
TROI_BOT_DEBUG_USER_ID = 19055


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
        SELECT pl.id
             , pl.mbid
             , pl.creator_id
             , pl.name
             , pl.description
             , pl.public
             , pl.created
             , pl.last_updated
             , pl.copied_from_id
             , pl.created_for_id
             , pl.algorithm_metadata
             , copy.mbid as copied_from_mbid
          FROM playlist.playlist AS pl
     LEFT JOIN playlist.playlist AS copy
            ON pl.copied_from_id = copy.id
         WHERE pl.mbid = :mbid""")
    with ts.engine.connect() as connection:
        result = connection.execute(query, {"mbid": playlist_id})
        obj = result.mappings().first()
        if not obj:
            return None
        obj = dict(obj)
        user_id = obj['creator_id']
        user = db_user.get(user_id)
        obj['creator'] = user['musicbrainz_id']
        if obj['created_for_id']:
            created_for_user = db_user.get(obj['created_for_id'])
            if created_for_user:
                obj['created_for'] = created_for_user['musicbrainz_id']

        if load_recordings:
            playlist_map = get_recordings_for_playlists(connection, [obj['id']])
            obj['recordings'] = playlist_map.get(obj['id'], [])
        else:
            obj['recordings'] = []
        playlist_collaborator_ids = get_collaborators_for_playlists(connection, [obj['id']])
        collaborator_ids_list = playlist_collaborator_ids.get(obj['id'], [])
        obj['collaborator_ids'] = collaborator_ids_list
        obj['collaborators'] = get_collaborators_names_from_ids(collaborator_ids_list)
        return model_playlist.Playlist.parse_obj(obj)


def get_playlists_for_user(user_id: int,
                           include_private: bool = False,
                           load_recordings: bool = False,
                           count: int = 0,
                           offset: int = 0):
    """Get all playlists that a user created

    Arguments:
        user_id: The user to find playlists for
        include_private: If True, include all playlists by a user, including private ones. The count of
                         playlists returned will include private playlists if True
        load_recordings: If true, load the recordings for the playlist too
        count: Return max count number of playlists, for pagination purposes. If omitted, return all.
        offset: Return playlists starting at offset, for pagination purposes. Default 0.

    Raises:

    Returns:
        A tuple of (Playlists created by the given user, total number of playlists for a user)

    """

    if count == 0:
        count = None

    params = {"creator_id": user_id, "count": count, "offset": offset}
    where_public = ""
    if not include_private:
        where_public = "AND pl.public = :public"
        params["public"] = True
    query = sqlalchemy.text(f"""
        SELECT pl.id
             , pl.mbid
             , pl.creator_id
             , pl.name
             , pl.description
             , pl.public
             , pl.created
             , pl.last_updated
             , pl.copied_from_id
             , pl.created_for_id
             , pl.algorithm_metadata
             , copy.mbid as copied_from_mbid
          FROM playlist.playlist AS pl
     LEFT JOIN playlist.playlist AS copy
            ON pl.copied_from_id = copy.id
         WHERE pl.creator_id = :creator_id
               {where_public}
      ORDER BY pl.created DESC
         LIMIT :count
        OFFSET :offset""")

    with ts.engine.connect() as connection:
        result = connection.execute(query, params)
        playlists = _playlist_resultset_to_model(connection, result, load_recordings)

        # Now fetch the count of playlists
        params = {"creator_id": user_id}
        where_public = ""
        if not include_private:
            where_public = "AND public = :public"
            params["public"] = True
        query = sqlalchemy.text(f"""SELECT COUNT(*)
                                      FROM playlist.playlist
                                     WHERE creator_id = :creator_id
                                           {where_public}""")
        count = connection.execute(query, params).fetchone()[0]

    return playlists, count


def _playlist_resultset_to_model(connection, result, load_recordings):
    """Parse the result of an sql query to get playlists

    Fill in related data (username, created_for username) and collaborators
    """
    playlists = []
    user_id_map = {}
    for row in result.mappings():
        row = dict(row)
        creator_id = row["creator_id"]
        if creator_id not in user_id_map:
            # TODO: Do this lookup in bulk
            user_id_map[creator_id] = db_user.get(creator_id)
        created_for_id = row["created_for_id"]
        if created_for_id and created_for_id not in user_id_map:
            user_id_map[created_for_id] = db_user.get(created_for_id)
        row["creator"] = user_id_map[creator_id]["musicbrainz_id"]
        if created_for_id:
            row["created_for"] = user_id_map[created_for_id]["musicbrainz_id"]
        row["recordings"] = []
        playlist = model_playlist.Playlist.parse_obj(row)
        playlists.append(playlist)

    playlist_ids = [p.id for p in playlists]
    if playlist_ids:
        if load_recordings:
            playlist_recordings = get_recordings_for_playlists(connection, playlist_ids)
            for p in playlists:
                p.recordings = playlist_recordings.get(p.id, [])
        playlist_collaborator_ids = get_collaborators_for_playlists(connection, playlist_ids)
        for p in playlists:
            p.collaborator_ids = playlist_collaborator_ids.get(p.id, [])
            p.collaborators = get_collaborators_names_from_ids(p.collaborator_ids)

    return playlists


def get_playlists_created_for_user(user_id: int,
                                   load_recordings: bool = False,
                                   count: int = 0,
                                   offset: int = 0):
    """Get all playlists that were created for a user by bots

    Arguments:
        user_id
        load_recordings
        count: Return max count number of playlists, for pagination purposes. If omitted, return all.
        offset: Return playlists starting at offset, for pagination purposes. Default 0.

    Raises:

    Returns:

    """

    if count == 0:
        count = None

    params = {"created_for_id": user_id, "count": count, "offset": offset}
    query = sqlalchemy.text(f"""
        SELECT pl.id
             , pl.mbid
             , pl.creator_id
             , pl.name
             , pl.description
             , pl.public
             , pl.created
             , pl.last_updated
             , pl.copied_from_id
             , pl.created_for_id
             , pl.algorithm_metadata
             , copy.mbid as copied_from_mbid
          FROM playlist.playlist AS pl
     LEFT JOIN playlist.playlist AS copy
            ON pl.copied_from_id = copy.id
         WHERE pl.created_for_id = :created_for_id
      ORDER BY pl.created DESC
         LIMIT :count
        OFFSET :offset""")

    with ts.engine.connect() as connection:
        result = connection.execute(query, params)
        playlists = _playlist_resultset_to_model(connection, result, load_recordings)

        # Fetch the total count of playlists
        params = {"created_for_id": user_id}
        query = sqlalchemy.text(f"""SELECT COUNT(*)
                                      FROM playlist.playlist
                                     WHERE created_for_id = :created_for_id""")
        count = connection.execute(query, params).fetchone()[0]

    return playlists, count


def get_playlists_collaborated_on(user_id: int,
                                  include_private: bool = False,
                                  load_recordings: bool = False,
                                  count: int = 0,
                                  offset: int = 0):
    """Get playlists that this user doesn't own, but is a collaborator on.
    Playlists are ordered by creation date.

    Arguments:
        user_id: The user id
        load_recordings: If True, also return recordings for each playlist
        include_private: If True, include all playlists by a user, including private ones. The count of
                 playlists returned will include private playlists if True
        count: Return this many playlists. If 0, return all playlists
        offset: if set, get playlists from this offset

    Returns:
        a tuple (playlists, total_playlists)
    """
    if count == 0:
        count = None

    params = {"collaborator_id": user_id, "count": count, "offset": offset}
    where_public = ""
    if not include_private:
        where_public = "AND pl.public = :public"
        params["public"] = True
    query = sqlalchemy.text(f"""
        SELECT pl.id
             , pl.mbid
             , pl.creator_id
             , pl.name
             , pl.description
             , pl.public
             , pl.created
             , pl.last_updated
             , pl.copied_from_id
             , pl.created_for_id
             , pl.algorithm_metadata
             , copy.mbid as copied_from_mbid
          FROM playlist.playlist AS pl
     LEFT JOIN playlist.playlist AS copy
            ON pl.copied_from_id = copy.id
     LEFT JOIN playlist.playlist_collaborator
            ON pl.id = playlist_collaborator.playlist_id
         WHERE playlist.playlist_collaborator.collaborator_id = :collaborator_id
               {where_public}
      ORDER BY pl.created DESC
         LIMIT :count
        OFFSET :offset""")

    with ts.engine.connect() as connection:
        result = connection.execute(query, params)
        playlists = _playlist_resultset_to_model(connection, result, load_recordings)

        # Fetch the total count of playlists
        params = {"collaborator_id": user_id}
        where_public = ""
        if not include_private:
            where_public = "AND playlist.public = :public"
            params["public"] = True
        query = sqlalchemy.text(f"""SELECT COUNT(*)
                                      FROM playlist.playlist
                                 LEFT JOIN playlist.playlist_collaborator
                                        ON playlist.playlist.id = playlist_collaborator.playlist_id
                                     WHERE playlist.playlist_collaborator.collaborator_id = :collaborator_id
                                           {where_public}""")
        count = connection.execute(query, params).fetchone()[0]

    return playlists, count


def get_collaborators_for_playlists(connection, playlist_ids: List[int]):
    """Get all of the collaborators for the given playlists

    Args:
        connection: an open database connection
        playlist_ids: a list of playlist ids to get collaborator information for

    Return:
        a dictionary of {playlist_id: [collaborator_ids]}
    """
    if not playlist_ids:
        return {}

    query = sqlalchemy.text("""
        SELECT playlist_id
             , array_agg(collaborator_id) AS collaborator_ids
          FROM playlist.playlist_collaborator
         WHERE playlist_id in :playlist_ids
      GROUP BY playlist_id""")
    result = connection.execute(query, {"playlist_ids": tuple(playlist_ids)})
    ret = {}
    for row in result.fetchall():
        ret[row.playlist_id] = row.collaborator_ids
    return ret


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
    for row in result.mappings():
        row = dict(row)
        added_by_id = row["added_by_id"]
        if added_by_id not in user_id_map:
            # TODO: Do this lookup in bulk
            user_id_map[added_by_id] = db_user.get(added_by_id)
        row["added_by"] = user_id_map[added_by_id]["musicbrainz_id"]
        playlist_recording = model_playlist.PlaylistRecording.parse_obj(row)
        playlist_recordings_map[playlist_recording.playlist_id].append(playlist_recording)
    for playlist_id in playlist_ids:
        if playlist_id not in playlist_recordings_map:
            playlist_recordings_map[playlist_id] = []
    return dict(playlist_recordings_map)


def _remove_old_collaborative_playlists(connection, creator_id: int, created_for_id: int, source_patch: str):
    """
       Remove all the collaborative playlists for the given creator, credit_for and source_patch.
       This function will be used in the create function in order to remove the old collaborative playlists
       that the new playlist replaces, all in one transaction.
    """
    del_query = sqlalchemy.text("""DELETE FROM playlist.playlist
                                         WHERE creator_id = :creator_id
                                           AND algorithm_metadata->>'source_patch' = :source_patch
                                           AND created_for_id = :created_for_id""")
    connection.execute(del_query, {"creator_id": creator_id,
                                   "created_for_id": created_for_id,
                                   "source_patch": source_patch})


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

    # TODO: In a way this is less than ideal -- the caller must take the string name and find the ID,
    # and then the name is fetched for verification again. Should we accept created_for here and do
    # lookup only here and not he in the API call validation?
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
                                    'copied_from_id', 'created_for_id'})
    fields["algorithm_metadata"] = ujson.dumps(playlist.algorithm_metadata or {})

    with ts.engine.connect() as connection:
        with connection.begin():
            # This code seems out of place for a create function, but in order to keep the deletion of
            # old collaborative playlists in the same transaction as creating new playlists, it needs to
            # to be here.
            if playlist.creator_id == TROI_BOT_USER_ID and playlist.created_for_id is not None and \
                    playlist.algorithm_metadata is not None and "source_patch" in playlist.algorithm_metadata:
                _remove_old_collaborative_playlists(
                    connection,
                    playlist.creator_id,
                    playlist.created_for_id,
                    playlist.algorithm_metadata["source_patch"]
                )

            result = connection.execute(query, fields)
            row = result.fetchone()
            playlist.id = row.id
            playlist.mbid = row.mbid
            playlist.created = row.created
            playlist.creator = creator["musicbrainz_id"]
            playlist.recordings = insert_recordings(connection, playlist.id, playlist.recordings, 0)

            if playlist.collaborator_ids:
                add_playlist_collaborators(connection, playlist.id, playlist.collaborator_ids)
                collaborator_ids = get_collaborators_for_playlists(connection, [playlist.id])
                collaborator_ids = collaborator_ids.get(playlist.id, [])
                playlist.collaborators = get_collaborators_names_from_ids(collaborator_ids)

            return model_playlist.Playlist.parse_obj(playlist.dict())


def add_playlist_collaborators(connection, playlist_id, collaborator_ids):
    delete_query = sqlalchemy.text(
        """DELETE FROM playlist.playlist_collaborator
                 WHERE playlist_id = :playlist_id""")
    insert_query = sqlalchemy.text(
        """INSERT INTO playlist.playlist_collaborator (playlist_id, collaborator_id)
                VALUES (:playlist_id, :collaborator_id)""")

    collaborator_params = [{"playlist_id": playlist_id, "collaborator_id": c_id} for c_id in collaborator_ids]
    connection.execute(delete_query, {"playlist_id": playlist_id})
    if collaborator_params:
        connection.execute(insert_query, collaborator_params)


def get_collaborators_names_from_ids(collaborator_ids: List[int]):
    collaborators = []
    # TODO: Look this up in one query
    for user_id in collaborator_ids:
        user = db_user.get(user_id)
        if user:
            collaborators.append(user["musicbrainz_id"])
    collaborators.sort()
    return collaborators


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
    with ts.engine.begin() as connection:
        params = playlist.dict(include={'id', 'name', 'description', 'public'})
        connection.execute(query, params)
        # Unconditionally add collaborators, this allows us to delete all collaborators
        # if [] is passed in.
        # TODO: Optimise this by getting collaborators from the database and only updating
        #  if what has passed is different to what exists
        add_playlist_collaborators(connection, playlist.id, playlist.collaborator_ids)
        collaborator_ids = get_collaborators_for_playlists(connection, [playlist.id])
        collaborator_ids = collaborator_ids.get(playlist.id, [])
        playlist.collaborators = get_collaborators_names_from_ids(playlist.collaborator_ids)
        playlist.last_updated = set_last_updated(connection, playlist.id)
        return playlist


def set_last_updated(connection, playlist_id):
    query = sqlalchemy.text("""
        UPDATE playlist.playlist
           SET last_updated = now()
         WHERE id = :playlist_id
     RETURNING last_updated""")
    result = connection.execute(query, {"playlist_id": playlist_id})
    return result.fetchone()[0]


def copy_playlist(playlist: model_playlist.Playlist, creator_id: int):
    newplaylist = playlist.copy()
    newplaylist.name = "Copy of " + newplaylist.name
    newplaylist.creator_id = creator_id
    newplaylist.copied_from_id = playlist.id
    newplaylist.created_for_id = None
    newplaylist.created_for = None
    newplaylist.collaborator_ids = []
    newplaylist.collaborators = []
    # TODO: We need a copied_from_mbid (calculated) field in the playlist object so we can show the mbid in the ui

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
    with ts.engine.begin() as connection:
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
        INSERT INTO playlist.playlist_recording (playlist_id, position, mbid, added_by_id, created)
                                         VALUES (:playlist_id, :position, :mbid, :added_by_id, :created)
                                      RETURNING id, created""")
    return_recordings = []
    user_id_map = {}
    insert_ts = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    for recording in recordings:
        if not recording.created:
            recording.created = insert_ts
        result = connection.execute(query, recording.dict(include={'playlist_id', 'position', 'mbid', 'added_by_id', 'created'}))
        if recording.added_by_id not in user_id_map:
            # TODO: Do this lookup in bulk
            user_id_map[recording.added_by_id] = db_user.get(recording.added_by_id)
        row = result.fetchone()
        recording.id = row.id
        recording.created = row.created
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
    with ts.engine.begin() as connection:
        delete_params = {"playlist_id": playlist.id,
                         "position_start": remove_from,
                         "position_end": remove_from+remove_count}
        connection.execute(delete, delete_params)
        if remove_from + remove_count < len(playlist.recordings):
            reorder_params = {"playlist_id": playlist.id,
                              "position": remove_from + remove_count,
                              "offset": -1 * remove_count}
            connection.execute(reorder, reorder_params)
        # TODO: In move_recordings we call delete and then add, so this is called twice
        set_last_updated(connection, playlist.id)


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
    with ts.engine.begin() as connection:
        if position < len(playlist.recordings):
            reorder_params = {"playlist_id": playlist.id,
                              "offset": len(recordings),
                              "position": position}
            connection.execute(reorder, reorder_params)
        recordings = insert_recordings(connection, playlist.id, recordings, position)
        playlist.recordings = playlist.recordings[0:position] + recordings + playlist.recordings[position:]
        set_last_updated(connection, playlist.id)
        return playlist


def move_recordings(playlist: model_playlist.Playlist, position_from: int, position_to: int, count: int):
    # TODO: This must be done in a single transaction
    removed = playlist.recordings[position_from:position_from+count]
    delete_recordings_from_playlist(playlist, position_from, count)
    add_recordings_to_playlist(playlist, removed, position_to)
