from flask import current_app
from datetime import datetime
from listenbrainz_spark.utils import get_listens
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark import path
from listenbrainz_spark.stats.user.utils import get_artists
from collections import defaultdict

def calculate():
    now = datetime.utcnow()
    listens_df = get_listens(from_date=datetime(LAST_FM_FOUNDING_YEAR, 1, 1), to_date=now, dest_path=current_app.config['HDFS_CLUSTER_URI']+path.LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'stats_user_all'
    listens_df.createOrReplaceTempView(table_name)

    data = defaultdict(dict)

    # calculate and put artist stats into the result
    artist_data = get_artists(table_name)
    messages = []

    for user_name, user_artists in artist_data.items():
        messages.append({
            'musicbrainz_id': user_name,
            'type': 'user_artist',
            'artist_stats': user_artists,
            'artist_count': len(user_artists ),
        })

    return messages
