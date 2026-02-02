from typing import Iterable

from psycopg2.extras import execute_values

from listenbrainz.db.recording import resolve_redirect_mbids


def load_artists_from_mbids_with_redirects(mb_curs, mbids: Iterable[str]) -> list[dict]:
    """ Given a list of mbids return a map with mbid as key and the artist info as value. """
    redirected_mbids, index, inverse_index = resolve_redirect_mbids(mb_curs, "artist", mbids)
    query = """
             WITH mbids (gid) AS (VALUES %s)
           SELECT a.gid::TEXT AS artist_mbid
                , a.name
                , a.comment
                , t.name AS type
                , g.name AS gender
             FROM musicbrainz.artist a
        LEFT JOIN musicbrainz.artist_type t
               ON t.id = a.type
        LEFT JOIN musicbrainz.gender g
               ON g.id = a.gender
             JOIN mbids m
               ON a.gid = m.gid::UUID
     """
    results = execute_values(mb_curs, query, [(mbid,) for mbid in redirected_mbids], fetch=True)
    metadata_idx = {row["artist_mbid"]: row for row in results}

    # Finally collate all the results, ensuring that we have one entry with original_recording_mbid for each input
    output = []
    for mbid in mbids:
        redirected_mbid = index.get(mbid, mbid)
        if redirected_mbid not in metadata_idx:
            item = {
                "artist_mbid": redirected_mbid,
                "name": None,
                "comment": None,
                "type": None,
                "gender": None,
                "original_artist_mbid": mbid
            }
        else:
            data = metadata_idx[redirected_mbid]
            item = dict(data)
            item["original_artist_mbid"] = mbid

        output.append(item)

    return output
