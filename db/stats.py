from db import create_cursor, commit, cache
import datetime
import time
import six


STATS_CACHE_TIMEOUT = 60 * 10  # ten minutes
LAST_MBIDS_CACHE_TIMEOUT = 60  # 1 minute (this query is cheap)


def get_last_submitted_recordings():
    last_submitted_data = cache.get('last-submitted-data')
    if not last_submitted_data:
        with create_cursor() as cursor:
            cursor.execute("""SELECT mbid,
                                     data->'metadata'->'tags'->'artist'->>0,
                                     data->'metadata'->'tags'->'title'->>0
                                FROM lowlevel
                            ORDER BY id DESC
                               LIMIT 5
                              OFFSET 10""")
            last_submitted_data = cursor.fetchall()
        last_submitted_data = [
            (r[0], r[1], r[2]) for r in last_submitted_data if r[1] and r[2]
        ]
        cache.set('last-submitted-data', last_submitted_data, time=LAST_MBIDS_CACHE_TIMEOUT)

    return last_submitted_data


def get_stats():
    stats_keys = ["lowlevel-lossy", "lowlevel-lossy-unique", "lowlevel-lossless", "lowlevel-lossless-unique"]
    # TODO: Port this to new implementation:
    stats = cache._mc.get_multi(stats_keys, key_prefix="ac-num-")
    last_collected = cache.get('last-collected')

    # Recalculate everything together, always.
    if sorted(stats_keys) != sorted(stats.keys()) or last_collected is None:
        stats_parameters = dict([(a, 0) for a in stats_keys])

        with create_cursor() as cursor:
            cursor.execute("SELECT now() as now, collected FROM statistics ORDER BY collected DESC LIMIT 1")
            update_db = False
            if cursor.rowcount > 0:
                (now, last_collected) = cursor.fetchone()
            if cursor.rowcount == 0 or now - last_collected > datetime.timedelta(minutes=59):
                update_db = True

            cursor.execute("SELECT lossless, count(*) FROM lowlevel GROUP BY lossless")
            for row in cursor.fetchall():
                if row[0]: stats_parameters['lowlevel-lossless'] = row[1]
                if not row[0]: stats_parameters['lowlevel-lossy'] = row[1]

            cursor.execute("SELECT lossless, count(*) FROM (SELECT DISTINCT ON (mbid) mbid, lossless FROM lowlevel ORDER BY mbid, lossless DESC) q GROUP BY lossless;")
            for row in cursor.fetchall():
                if row[0]: stats_parameters['lowlevel-lossless-unique'] = row[1]
                if not row[0]: stats_parameters['lowlevel-lossy-unique'] = row[1]

            if update_db:
                for key, value in six.iteritems(stats_parameters):
                    cursor.execute("INSERT INTO statistics (collected, name, value) VALUES (now(), %s, %s) RETURNING collected", (key, value))
                commit()

            cursor.execute("SELECT now()")
            last_collected = cursor.fetchone()[0]

        value = stats_parameters

        # TODO: Port this to new implementation:
        cache._mc.set_multi(stats_parameters, key_prefix="ac-num-", time=STATS_CACHE_TIMEOUT)
        cache.set('last-collected', last_collected, time=STATS_CACHE_TIMEOUT)
    else:
        value = stats

    return value, last_collected


def get_statistics_data():
    with create_cursor() as cursor:
        cursor.execute(
            "SELECT name, array_agg(collected ORDER BY collected ASC) AS times,"
            "       array_agg(value ORDER BY collected ASC) AS values "
            "FROM statistics "
            "GROUP BY name"
        )
        stats_key_map = {
            "lowlevel-lossy": "Lossy (all)",
            "lowlevel-lossy-unique": "Lossy (unique)",
            "lowlevel-lossless": "Lossless (all)",
            "lowlevel-lossless-unique": "Lossless (unique)"
        }
        ret = []
        total_unique = {"name": "Total (unique)", "data": {}}
        total_all = {"name": "Total (all)", "data": {}}
        for val in cursor:
            pairs = zip([_make_timestamp(v) for v in val[1]], val[2])
            ret.append({
                "name": stats_key_map.get(val[0], val[0]),
                "data": [[v[0], v[1]] for v in pairs]
            })
            second = {}
            if val[0] in ["lowlevel-lossy", "lowlevel-lossless"]:
                second = total_all
            elif val[0] in ["lowlevel-lossy-unique", "lowlevel-lossless-unique"]:
                second = total_unique
            for pair in pairs:
                if pair[0] in second['data']:
                    second['data'][pair[0]] = second['data'][pair[0]] + pair[1]
                else:
                    second['data'][pair[0]] = pair[1]

    total_unique['data'] = [[k, total_unique['data'][k]] for k in sorted(total_unique['data'].keys())]
    total_all['data'] = [[k, total_all['data'][k]] for k in sorted(total_all['data'].keys())]
    ret.extend([total_unique, total_all])
    return ret


def _make_timestamp(dt):
    return time.mktime(dt.utctimetuple())*1000 + dt.microsecond/1000
