import orjson
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal, Identifier

from listenbrainz.metadata_cache.models import Album, Artist, Track


def insert_album(curs, schema, album: Album, last_refresh, expires_at):
    """ Insert album data into normalized album table """
    query = SQL("""
        INSERT INTO {schema}.album (album_id, name, type, release_date, last_refresh, expires_at, data)
             VALUES (%(album_id)s, %(name)s, %(type)s, %(release_date)s, %(last_refresh)s, %(expires_at)s, %(data)s)
        ON CONFLICT (album_id)
          DO UPDATE
                SET name = EXCLUDED.name
                  , type = EXCLUDED.type
                  , release_date = EXCLUDED.release_date
                  , last_refresh = EXCLUDED.last_refresh
                  , expires_at = EXCLUDED.expires_at
                  , data = EXCLUDED.data
    """).format(schema=Identifier(schema))
    curs.execute(query, {
        "album_id": album.id,
        "name": album.name,
        "type": album.type_.value,
        "release_date": album.release_date,
        "last_refresh": last_refresh,
        "expires_at": expires_at,
        "data": orjson.dumps(album.data).decode("utf-8")
    })


def insert_artists(curs, schema, artists: list[Artist]):
    """ Insert artist in normalized artist table """
    query = SQL("""
        INSERT INTO {schema}.artist (artist_id, name, data)
             VALUES %s
        ON CONFLICT (artist_id)
          DO UPDATE
                SET name = EXCLUDED.name
                  , data = EXCLUDED.data
    """).format(schema=Identifier(schema))
    artist_ids = set()
    values = []
    for artist in artists:
        if artist.id not in artist_ids:
            values.append((artist.id, artist.name, orjson.dumps(artist.data).decode("utf-8")))
            artist_ids.add(artist.id)
    execute_values(curs, query, values)


def insert_album_artists(curs, schema, album_id: str, artists: list[Artist]):
    """ Insert album and artist ids in rel_album_artist table to mark which artist appear on which albums """
    # delete before insert so that if existing artists have changed the updates are captured properly.
    # say if an artist id was removed from the album then a ON CONFLICT DO UPDATE would insert the new artist
    # but not remove the outdated entry. so delete first and then insert.
    delete_query = SQL("DELETE FROM {schema}.rel_album_artist WHERE album_id = %(album_id)s") \
        .format(schema=Identifier(schema))
    curs.execute(delete_query, {"album_id": album_id})

    insert_query = SQL("INSERT INTO {schema}.rel_album_artist (album_id, artist_id, position) VALUES %s") \
        .format(schema=Identifier(schema))
    template = SQL("({album_id}, %s, %s)").format(album_id=Literal(album_id))
    values = [(a.id, idx) for idx, a in enumerate(artists)]
    execute_values(curs, insert_query, values, template)


def insert_tracks(curs, schema, album_id: str, tracks: list[Track]):
    """ Insert track data in normalized track tables """
    query = SQL("""
        INSERT INTO {schema}.track (track_id, name, track_number, album_id, data)
             VALUES %s
        ON CONFLICT (track_id)
          DO UPDATE
                SET name = EXCLUDED.name
                  , track_number = EXCLUDED.track_number
                  , album_id = EXCLUDED.album_id
                  , data = EXCLUDED.data
    """).format(schema=Identifier(schema))
    values = [(t.id, t.name, int(t.track_number), orjson.dumps(t.data).decode("utf-8")) for t in tracks]
    template = SQL("(%s, %s, %s, {album_id}, %s)").format(album_id=Literal(album_id))
    execute_values(curs, query, values, template)


def insert_track_artists(curs, schema, data: dict[str, list[Artist]]):
    """ Insert track and artist ids in rel_track_artists table to mark which tracks have which artists """
    delete_query = SQL("DELETE FROM {schema}.rel_track_artist WHERE track_id IN %s") \
        .format(schema=Identifier(schema))
    insert_query = SQL("INSERT INTO {schema}.rel_track_artist (track_id, artist_id, position) VALUES %s") \
        .format(schema=Identifier(schema))

    values = []
    track_ids = []
    for track_id, artists in data.items():
        track_ids.append(track_id)
        for idx, artist in enumerate(artists):
            values.append((track_id, artist.id, idx))

    # delete before insert so that if existing artists have changed the updates are captured properly.
    # say if an artist id was removed from a track then a ON CONFLICT DO UPDATE would insert the new artist
    # but not remove the outdated entry. so delete first and then insert.
    curs.execute(delete_query, (tuple(track_ids),))
    execute_values(curs, insert_query, values)


def insert(curs, schema, album: Album, last_refresh, expires_at):
    """ Main function to insert data in normalized tables """
    insert_album(curs, schema, album, last_refresh, expires_at)
    insert_artists(curs, schema, album.artists)
    insert_album_artists(curs, schema, album.id, album.artists)

    # Deduplicate track artists list before inserting otherwise ON CONFLICT DO UPDATE will complain that
    # it cannot update multiple times in 1 query. alternative is to insert 1 track's artists at a time.
    track_artists = {}
    all_artists = []
    artist_ids = set()
    for track in album.tracks:
        track_artists[track.id] = track.artists

        for artist in track.artists:
            if artist.id not in artist_ids:
                all_artists.append(artist)
                artist_ids.add(artist.id)

    insert_tracks(curs, schema, album.id, album.tracks)
    insert_artists(curs, schema, all_artists)
    insert_track_artists(curs, schema, track_artists)
