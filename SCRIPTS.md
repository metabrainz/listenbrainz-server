# Scripts

This is a table of the scripts that we can submit to Spark.


| Script          | Description                                                                           |
|-----------------|---------------------------------------------------------------------------------------|
| load_data.py    | loads a listenbrainz dump into spark and saves appropriate dataframes                 |
| train_models.py | uses the dataframes from load_data.py to train collaborative filtering models         |
| recommend.py    | uses the model trained by train_models.py to make recording recommendations for users |
| import.py       | imports a ListenBrainz dump into HDFS                                                 |

