FROM python:2.7.11

MAINTAINER Robert Kaye <rob@metabrainz.org>

# General setup
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                       python-redis \
                       redis-tools

RUN mkdir /code
WORKDIR /code

# These following steps are redundant, but they prevent the requirements from being installed too many times
RUN mkdir /code/redis-consumer
COPY ./redis-consumer/requirements.txt /code/redis-consumer
RUN pip install -r redis-consumer/requirements.txt

# This step is executed if our code changes, good.
COPY . /code
