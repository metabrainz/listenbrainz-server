import sys
import logging

from listenbrainz_spark.stats import user
from listenbrainz_spark.recommendations import create_dataframes
from listenbrainz_spark.recommendations import train_models
from listenbrainz_spark.recommendations import recommend
from listenbrainz_spark.recommendations import candidate_sets

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: manage.py <module_name>")
        sys.exit(-1)

    # The root logger always defaults to WARNING level
    # The level is changed from WARNING to INFO
    logging.getLogger().setLevel(logging.INFO)

    module_name = sys.argv[1]
    if module_name == 'create_dataframes':
        create_dataframes.main()
    elif module_name == 'train_models':
        train_models.main()
    elif module_name == 'recommend':
        recommend.main()
    elif module_name == 'candidate_sets':
        candidate_sets.main()
    elif module_name == 'user':
        user.main()
