ListenBrainz Collaborative Filtering
=====================
ListenBrainz collaborative filtering component to generate recommendations.

## About

The component uses collaborative filtering to recommend recordings to users based on their listening history. ListenBrainz uses Apache Spark to process the listening history of users and generate recommendations.

**Note**:  
- The listening history and supporting data used by ListenBrainz is heavy for the local environment. Releasing small test datasets to make the development experience smoother is on our roadmap.
- Spark sends the generated recommendations to ListenBrainz webserver containers as Rabbit MQ messages. Therefore before generating the recommendations, the `spark_reader` container should be running. For details, see the [Spark Architecture](https://listenbrainz.readthedocs.io/en/latest/developers/spark-architecture.html) document.


## Production environment

These instructions help to request recommendations from Spark cluster in prod.

To generate recommendations following data dumps must be imported into the spark cluster.

- **ListenBrainz Listens Data Dump**: The listens are regularly being imported into the cluster. We need not worry about it!
- **ListenBrainz MSID MBID Mapping Dump**: To import mapping into the cluster, issue the following command:

  `./develop.sh manage spark request_import_mapping`

  The mapping is live on [FTP](http://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz/labs/mappings/msid-mbid-mapping/)

- **ListenBrainz Artist Relation Dump**: To import artist relation into the cluster, issue the following command:

  `./develop.sh manage spark request_import_artist_relation`

  The artist relation is live on [FTP](http://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz/labs/artist-credit-artist-credit-relations/)

Once the data dumps have been imported into the cluster, we are good to move on to the recommendation generation process. Yay!

The recommendation generation process has been divided into four stages.

- **Stage 1**: Process user listening history.

  Send a request to spark cluster for generating dataframes and upload to HDFS.

  `./develop.sh manage spark request_dataframes --days=X`

  where X is the number of days of listening history you want to train the model on. By default, X is equal to 180 i.e. last 6 months from the date on which the script is invoked.

- **Stage 2**: Train the model.

  Send a request to spark cluster to train the model and upload to HDFS.

  `./develop.sh manage spark request_model --rank=X --itr=Y --lmbda=Z --alpha=M`

  where X is the rank or number of hidden features. For example, if rank = [12, 7, 8], it should be passed as follows:

  `--rank=12 --rank=7 --rank=8`

  By default , rank = [5, 10]

  where Y is iteration or number of iterations to run. For example, if itr = [3, 6, 8], it should be passed as follows:

  `--itr=3 --itr=6 --itr=8`

  By default, itr = [5, 10]

  where Z is lambda or overfitting control factor. For example, if lmbda = [4.8, 1.2, 4.4], it should be passed as follows:

  `--lmbda=4.8 --lmbda=1.2 --lmbda=4.4`

  By default, lmbda = [0.1, 10.0]

  where M is alpha or baseline level of confidence weighting applied. For example, if alpha = 7.1, it should be passed as follows:

  `--alpha=7.1`

  By default, alpha = 3.0

  For more information on model parameters refer to the [official documentation](https://spark.apache.org/docs/2.1.0/mllib-collaborative-filtering.html).


- **Stage 3**: Generate candidate sets.

  Send a request to spark cluster to generate candidate sets and upload to HDFS. For each user, personalized sets are generated which contain recordings of top artists listened to by the user and recordings of artists similar to top artists listened to by the user.

  `./develop.sh manage spark request_candidate_sets --days=X --top=Y --similar=Z --user-name=M --html`

  where X is the number of days on which recommendations should be generated. By default, X is equal to 7 i.e. last week from the date on which the script is invoked.

  where Y is the number of top artists to fetch for a user from the artists listened to by the user in the last X days. By default, Y is equal to 20.

  where Z is the number of artists similar to top artists to fetch for a user. By default, Z is equal to 20.

  where M is user name or musicbrainz id of the users to generate candidate sets for. For example, if candidate sets shall be generated for 'vansika', 'rob', 'ram', it should be passed as follows:

  `--user-name=vansika --user-name=rob --user-name=ram`

  By default, user name is an empty list i.e. generate candidate sets for all active users.

  To generate HTML file for candidate sets, set the `html` flag.

  ***Note***: Recommendations will be only generated for users with candidate sets.

- **Stage 4**: Generate recommendations

  Send a request to spark cluster to generate and return recommendations.

  `./develop.sh manage spark request_recommendations --top=X --similar=Y --user-name=Z`

  where X is the number of recommended recordings for a user from the top artist candidate set. By default, X is equal to 200.

  where Y is the number of recommended recordings for a user from the similar artist candidate set. By default, Y is equal to 200.

  where Z is user name or musicbrainz id of the users to generate recommendations for. For example, if recommendations shall be generated for 'vansika', 'rob', 'ram', it should be passed as follows:

  `--user-name=vansika --user-name=rob --user-name=ram`

  By default, user name is an empty list i.e. generate recommendations for all active users.


If you pass through all the four stages successfully; congratulations, the recommendations are all yours. Feel free to give us feedback to improve the music we serve :)


## License Notice

```
listenbrainz-server - Server for the ListenBrainz project

Copyright (C) 2017 MetaBrainz Foundation Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
```
