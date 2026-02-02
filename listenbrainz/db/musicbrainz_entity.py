from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Identifier


def _resolve_mbids_helper(curs, query, mbids):
    """ Helper to extract common code for resolving redirect and canonical mbids """
    result = execute_values(curs, query, [(mbid,) for mbid in mbids], fetch=True)
    index, inverse_index = {}, {}
    for row in result:
        old_mbid = row[0]
        new_mbid = row[1]
        index[old_mbid] = new_mbid
        inverse_index[new_mbid] = old_mbid

    new_mbids = []
    for mbid in mbids:
        # redirect the mbid to find the new entity if one exists otherwise use the original mbid itself
        new_mbids.append(index.get(mbid, mbid))

    return new_mbids, index, inverse_index


def resolve_redirect_mbids(curs, table, mbids):
    """ Given a list of mbids, resolve redirects if any and return the list of new mbids, a dict of
    redirected mbids and a reverse index of the same.
    """
    redirect_table = table + "_gid_redirect"
    query = SQL("""
          WITH mbids (gid) AS (VALUES %s)
        SELECT redirect.gid::TEXT AS old
             , target.gid::TEXT AS new
          FROM {redirect_table} redirect
          JOIN mbids
            ON redirect.gid = mbids.gid::UUID
          JOIN {target_table} target
            ON target.id = redirect.new_id
    """).format(target_table=Identifier("musicbrainz", table), redirect_table=Identifier("musicbrainz", redirect_table))
    return _resolve_mbids_helper(curs, query, mbids)
