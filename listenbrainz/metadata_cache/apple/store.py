import orjson
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal


def insert_album(curs, data, last_refresh, expires_at):
    """ Insert album data into normalized album table """
    if data["attributes"]["isSingle"]:
        album_type = "Single"
    elif data["attributes"]["isCompilation"]:
        album_type = "Compilation"
    else:
        album_type = "Album"
    query = """
        INSERT INTO apple_cache.album (apple_id, name, type, release_date, last_refresh, expires_at, data)
             VALUES (%(apple_id)s, %(name)s, %(type)s, %(release_date)s, %(last_refresh)s, %(expires_at)s, %(data)s)
        ON CONFLICT (apple_id)
          DO UPDATE
                SET name = EXCLUDED.name
                  , type = EXCLUDED.type
                  , release_date = EXCLUDED.release_date
                  , last_refresh = EXCLUDED.last_refresh
                  , expires_at = EXCLUDED.expires_at
                  , data = EXCLUDED.data
    """
    curs.execute(query, {
        "apple_id": data["id"],
        "name": data["attributes"]["name"],
        "type": album_type,
        "release_date": data["attributes"]["releaseDate"],
        "last_refresh": last_refresh,
        "expires_at": expires_at,
        "data": orjson.dumps(data).decode("utf-8")
    })


def insert_artists(curs, data):
    """ Insert artist in normalized artist table """
    artist_ids = set()
    query = """
        INSERT INTO apple_cache.artist (apple_id, name, data)
             VALUES %s
        ON CONFLICT (apple_id)
          DO UPDATE
                SET name = EXCLUDED.name
                  , data = EXCLUDED.data
    """
    values = []
    for artist in data:
        artist.pop("relationships")
        if artist["id"] not in artist_ids:
            values.append((artist["id"], artist["attributes"]["name"], orjson.dumps(artist).decode("utf-8")))
            artist_ids.add(artist["id"])
    execute_values(curs, query, values)


def insert_album_artists(curs, album_id, data):
    """ Insert album and artist ids in rel_album_artist table to mark which artist appear on which albums """
    # delete before insert so that if existing artists have changed the updates are captured properly.
    # say if an artist id was removed from the album then a ON CONFLICT DO UPDATE would insert the new artist
    # but not remove the outdated entry. so delete first and then insert.
    delete_query = "DELETE FROM apple_cache.rel_album_artist WHERE album_id = %(album_id)s"
    curs.execute(delete_query, {"album_id": album_id})

    insert_query = "INSERT INTO apple_cache.rel_album_artist (album_id, artist_id, position) VALUES %s"
    template = SQL("({album_id}, %s, %s)").format(album_id=Literal(album_id))
    values = [(a["id"], idx) for idx, a in enumerate(data)]
    execute_values(curs, insert_query, values, template)


def insert_tracks(curs, album_id, data):
    """ Insert track data in normalized track tables """
    query = """
        INSERT INTO apple_cache.track (apple_id, name, track_number, album_id, data)
             VALUES %s
        ON CONFLICT (apple_id)
          DO UPDATE
                SET name = EXCLUDED.name
                  , track_number = EXCLUDED.track_number
                  , album_id = EXCLUDED.album_id
                  , data = EXCLUDED.data
    """
    values = [
        (t["id"], t["attributes"]["name"], int(t["attributes"]["trackNumber"]), orjson.dumps(t).decode("utf-8"))
        for t in data
    ]
    template = SQL("(%s, %s, %s, {album_id}, %s)").format(album_id=Literal(album_id))
    execute_values(curs, query, values, template)


def insert_track_artists(curs, data):
    """ Insert track and artist ids in rel_track_artists table to mark which tracks have which artists """
    delete_query = "DELETE FROM apple_cache.rel_track_artist WHERE track_id IN %s"
    insert_query = "INSERT INTO apple_cache.rel_track_artist (track_id, artist_id, position) VALUES %s"

    values = []
    track_ids = []
    for track_id, artists in data.items():
        track_ids.append(track_id)
        for idx, artist in enumerate(artists):
            values.append((track_id, artist["id"], idx))

    # delete before insert so that if existing artists have changed the updates are captured properly.
    # say if an artist id was removed from a track then a ON CONFLICT DO UPDATE would insert the new artist
    # but not remove the outdated entry. so delete first and then insert.
    curs.execute(delete_query, (tuple(track_ids),))
    execute_values(curs, insert_query, values)


def insert(curs, album, last_refresh, expires_at):
    """ Main function to insert data in normalized apple tables """
    album_artists = album.pop("artists")
    tracks = album.pop("tracks")

    insert_album(curs, album, last_refresh, expires_at)
    insert_artists(curs, album_artists)
    insert_album_artists(curs, album["id"], album_artists)

    # Deduplicate track artists list before inserting otherwise ON CONFLICT DO UPDATE will complain that
    # it cannot update multiple times in 1 query. alternative is to insert 1 track's artists at a time.
    track_artists = {}
    all_artists = []
    artist_ids = set()
    for track in tracks:
        artists = track.pop("relationships")["artists"]["data"]
        track_artists[track["id"]] = artists

        for artist in artists:
            if artist["id"] not in artist_ids:
                all_artists.append(artist)
                artist_ids.add(artist["id"])

    insert_tracks(curs, album["id"], tracks)
    insert_artists(curs, all_artists)
    insert_track_artists(curs, track_artists)
