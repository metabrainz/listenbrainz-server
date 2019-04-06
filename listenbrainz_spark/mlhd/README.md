# Music Listening History Dataset analysis

We're playing with the [Music Listening History Dataset](http://ddmal.music.mcgill.ca/research/musiclisteninghistoriesdataset) in this module.

The general idea is to create a dataframe of all the 27B listens in the dataset.
To set this up, we have the following scripts.

* `hdfs_upload.py` - extract the listen files and upload to HDFS
* `create_dataframe.py` - create a dataframe out of the listen files in HDFS and save it


Once the dataframe is created, we can create more scripts to analyze the data, get
useful information etc. The first thing that we've worked on is artist popularity i.e.
which artists have been listened to the most in the dataset.

A comprehensive list of analysis scripts should be added soon.
