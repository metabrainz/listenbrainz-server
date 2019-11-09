from datetime import datetime
from listenbrainz_spark.utils import get_listens
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats.user.utils import get_artists, get_recordings, get_releases

def calculate():
    now = datetime.utcnow()
    listens_df = get_listens(from_date=datetime(LAST_FM_FOUNDING_YEAR, 1, 1), to_date=now)
    table_name = 'stats.user.all'
    listens_df.createOrReplaceTempView(table_name)

    data = defaultdict(dict)

    # calculate and put artist stats into the result
    artist_data = get_artists(table)
    for user_name, user_artists in artist_data.items():
        data[user_name]['artists'] = {
            'artist_stats': user_artists,
            'artist_count': len(user_artists ),
        }

    # calculate and put recording stats into the result
    recording_data = get_recordings(table)
    for user_name, recording_stats in recording_data.items():
        data[user_name]['recordings'] = recording_stats

    # calculate and put release stats into the result
    release_data = get_releases(table)
    for user_name, release_stats in release_data.items():
        data[user_name]['releases'] = release_stats

    return data
