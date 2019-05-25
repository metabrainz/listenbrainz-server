import sys
from listenbrainz_spark.recommendations import create_dataframes
from listenbrainz_spark.recommendations import train_models
from listenbrainz_spark.recommendations import recommend

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: manage.py <module_name>")
        sys.exit(-1)

    module_name = sys.argv[1]
    if module_name == 'create_dataframes':
        create_dataframes.main()
    elif module_name == 'train_models':
        train_models.main()
    elif module_name == 'recommend':
        recommend.main()