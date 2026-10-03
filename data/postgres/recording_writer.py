WRITER_LINK_GIDS = [
    'd59d99ea-23d4-4a80-b066-edca32ee158f',  # composer
    '3e48faba-ec01-47fd-8e89-30e81161661c',  # lyricist
    'a255bca1-b157-4518-9108-7b147dc3fc68',  # writer
]

PERFORMANCE_LINK_GID = 'a3005666-a872-32c3-ad06-98af558e99b0'  # recording-work "performance"

WRITER_LINK_GIDS_SQL = ", ".join(f"'{gid}'" for gid in WRITER_LINK_GIDS)


def get_recording_writer_cache_query():
    """ Retrieve composers/writers/lyricists for recordings by traversing:

        recording -> l_recording_work -> work -> l_artist_work -> artist

        Returns rows of (recording_mbid, writer_mbid, writer_name).
        A recording may have multiple writers, and one writer may appear
        for multiple recordings. DISTINCT collapses artists credited under
        multiple roles on the same work (e.g. both composer and lyricist)
        so a listen is only counted once per writer.
    """
    return f"""
        SELECT DISTINCT
               r.gid::text AS recording_mbid
             , a.gid::text AS writer_mbid
             , a.name AS writer_name
          FROM musicbrainz.recording r
          JOIN musicbrainz.l_recording_work lrw
            ON lrw.entity0 = r.id
          JOIN musicbrainz.link l1
            ON lrw.link = l1.id
          JOIN musicbrainz.link_type lt1
            ON l1.link_type = lt1.id
           AND lt1.gid = '{PERFORMANCE_LINK_GID}'
          JOIN musicbrainz.work w
            ON lrw.entity1 = w.id
          JOIN musicbrainz.l_artist_work law
            ON law.entity1 = w.id
          JOIN musicbrainz.link l2
            ON law.link = l2.id
          JOIN musicbrainz.link_type lt2
            ON l2.link_type = lt2.id
           AND lt2.gid IN ({WRITER_LINK_GIDS_SQL})
          JOIN musicbrainz.artist a
            ON law.entity0 = a.id
    """
