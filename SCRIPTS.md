# Scripts

This is a table of the scripts that we can submit to Spark.


| Script                | Description                                                                            |
|-----------------------|----------------------------------------------------------------------------------------|
| create_dataframes.py  | loads a listenbrainz dump into spark and saves appropriate dataframes                  |
|----------------------------------------------------------------------------------------------------------------|
| train_models.py       | uses the dataframes from create_dataframes.py to train and save collaborative filtering|
|                       | models                                                                                 |
|----------------------------------------------------------------------------------------------------------------|
| candidate_sets.py     | loads a listenbrainz dump into spark and uses the dataframes from create_dataframes.py |
|                       | to generate and save candidate sets for each user                                      |
|----------------------------------------------------------------------------------------------------------------|
| recommend.py          | uses the model trained by train_models.py and candidate sets to make recording         |
|                       | recommendations for users                                                              |
|----------------------------------------------------------------------------------------------------------------|
| import.py             | imports a ListenBrainz dump into HDFS                                                  |
