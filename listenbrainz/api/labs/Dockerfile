FROM metabrainz/python:3.7

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                       git \
                       uwsgi \
                       uwsgi-plugin-python3 \
    && pip install --upgrade pip

RUN mkdir -p /code/hoster
WORKDIR /code/hoster

COPY consul-template.conf /etc
COPY ./uwsgi.service /etc/service/uwsgi/run
RUN chmod 755 /etc/service/uwsgi/run
COPY ./uwsgi.ini /etc/uwsgi/uwsgi.ini

COPY requirements.txt /code/hoster
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . /code/hoster
