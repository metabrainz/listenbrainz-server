FROM python:2.7.11

MAINTAINER Robert Kaye <rob@metabrainz.org>

RUN mkdir /code
WORKDIR /code

# These following steps are redundant, but they prevent the requirements from being installed too many times
RUN mkdir /code/influx-writer
COPY ./influx-writer/requirements.txt /code/influx-writer
RUN pip install -r /code/influx-writer/requirements.txt

# This step is executed if our code changes, good.
COPY . /code
