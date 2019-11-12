from datetime import datetime
from listenbrainz_spark.utils import get_listens
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats.user.utils import get_artists, get_recordings, get_releases
from collections import defaultdict

def calculate():
    now = datetime.utcnow()
    listens_df = get_listens(from_date=datetime(LAST_FM_FOUNDING_YEAR, 1, 1), to_date=now)
    table_name = 'stats_user_all'
    listens_df.createOrReplaceTempView(table_name)

    data = defaultdict(dict)

    # calculate and put artist stats into the result
    artist_data = get_artists(table_name)
    for user_name, user_artists in artist_data.items():
        data[user_name]['artists'] = {
            'artist_stats': user_artists,
            'artist_count': len(user_artists ),
        }

    return data
