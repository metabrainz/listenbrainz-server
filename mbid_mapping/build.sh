#!/bin/sh

docker build --pull -t metabrainz/mbid-mapping --target mbid-mapping-base .
