Recommendation engine
=====================
ListenBrainz recommendation engine using collaborative filtering.

## About

The recommendation engine uses collaborative filtering to recommend recordings to users based on their listening history. ListenBrainz uses Apache Spark to process the listening history of users and generate recommendations.

**Note**:  The listening history and supporting data used by ListenBrainz is heavy for the local environment. We are trying to release small test datasets soon to make the development experience smooth.


## Production environemnt

These instructions help to request recommendations from spark cluster in prod.

The recommendation generation process has been divided into four stages.

- **Stage 1**: Process user listening history.

  Send a request to spark cluster for generating dataframes.

  `./develop.sh manage spark request_dataframes --days=X`

  where X is the number of days of listening history you want to train the model on. By default, X is equal to 180 i.e. last 6 months from the date on which the script is invoked.

- **Stage 2**: Train the model.

  Send a request to spark cluster to train the model.

  `./develop.sh manage spark request_model`

- **Stage 3**: Generate candidate sets.

  Send a request to spark cluster to generate candidate sets. For each user, personalized sets are generated which contain recordings of top artists listened to by the user and recordings of artists similar to top artists listened to by the user.

  `./develop.sh manage spark request_candidate_sets --days=X --top=Y --similar=Z`

  where X is the number of days on which recommendations should be generated. By default, X is equal to 7 i.e. last week from the date on which the script is invoked.

  where Y is the number of top artists to fetch for a user from the artists listened to by the user in the last X days. By default, Y is equal to 20.

  where Z is the number of artists similar to top artists to fetch for a user. By default, Z is equal to 20.

- **Stage 4**: Generate recommendations

  Send a request to spark cluster to generate recommendations.

  `./develop.sh manage spark request_recommendations --top=X --similar=Y`

  where X is the number of recommended recordings for a user from the top artists candidate set. By default, X is equal to 200.

  where Y is the number of recommended recordings for a user from the similar artists candidate set. By default, Y is equal to 200.

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
