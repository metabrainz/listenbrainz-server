FROM metabrainz/python:3.7

RUN apt-get update && apt-get install -y ca-certificates && \
        pip install --upgrade pip

RUN groupadd --gid 901 listenbrainz
RUN useradd --create-home --shell /bin/bash --uid 901 --gid 901 listenbrainz

RUN mkdir -p /code/mapper && chown listenbrainz:listenbrainz /code/mapper
WORKDIR /code/mapper

# service start up scripts
COPY docker/consul-template.conf /etc/consul-template.conf

# Add cron jobs
COPY docker/crontab /etc/cron.d/mapper
RUN chmod 0644 /etc/cron.d/mapper

COPY --chown=listenbrainz:listenbrainz requirements.txt /code/mapper
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY --chown=listenbrainz:listenbrainz . /code/mapper
