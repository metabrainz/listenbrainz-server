#!/usr/bin/env python3

import sys
import psycopg2

import config


SELECT_ARTIST_RELATIONS_QUERY = '''
    SELECT count, arr.artist_0, a0.name AS artist_name_0, arr.artist_1, a1.name AS artist_name_1
      FROM relations.artist_artist_relations arr
      JOIN artist a0 ON arr.artist_0 = a0.id
      JOIN artist a1 ON arr.artist_1 = a1.id
     WHERE (arr.artist_0 = %s OR arr.artist_1 = %s)
  ORDER BY count desc
'''

SELECT_ARTIST_CREDIT_RELATIONS_QUERY = '''
    SELECT count, arr.artist_credit_0, a0.name AS artist_name_0, arr.artist_credit_1, a1.name AS artist_name_1
      FROM relations.artist_credit_artist_credit_relations arr
      JOIN artist a0 ON arr.artist_credit_0 = a0.id
      JOIN artist a1 ON arr.artist_credit_1 = a1.id
     WHERE (arr.artist_credit_0 = %s OR arr.artist_credit_1 = %s)
  ORDER BY count desc
'''


def get_artist_credit_similarities(artist_credit_id):
    '''
        Fetch artist credit relations for the given artist_credit_id.
    '''

    return _get_similarities(SELECT_ARTIST_CREDIT_RELATIONS_QUERY, artist_credit_id)


def get_artist_similarities(artist_id):
    '''
        Fetch artist relations for the given artist_mbid.
    '''

    return _get_similarities(SELECT_ARTIST_RELATIONS_QUERY, artist_id)


def _get_similarities(query, id):
    '''
        The actual function that does the real work.
    '''

    with psycopg2.connect(config.DB_CONNECT) as conn:
        with conn.cursor() as curs:
            curs.execute(query, (id, id))
            relations = []
            while True:
                row = curs.fetchone()
                if not row:
                    break

                if id == row[1]:
                    relations.append({
                        'count': row[0],
                        'id': row[3],
                        'artist_name': row[4]
                    })
                else:
                    relations.append({
                        'count': row[0],
                        'id': row[1],
                        'artist_name': row[2]
                    })

            return relations
