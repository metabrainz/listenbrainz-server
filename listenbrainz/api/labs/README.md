build
-----

docker build -t metabrainz/msid-mapping-hoster .

debug
-----

docker run -rm -p 8000:80 --name msid-mapping-hoster --network musicbrainzdocker_default metabrainz/msid-mapping-hoster

host
----

docker run -d -p 8000:80 --name msid-mapping-hoster --network musicbrainzdocker_default metabrainz/msid-mapping-hoster
