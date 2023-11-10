FROM metabrainz/python:3.10-20220315 as mbid-mapping-base

RUN apt-get update && apt-get install -y ca-certificates python3-pip netpbm git && \
        pip install --upgrade pip

RUN groupadd --gid 901 listenbrainz
RUN useradd --create-home --shell /bin/bash --uid 901 --gid 901 listenbrainz

RUN mkdir -p /code/mapper && chown listenbrainz:listenbrainz /code/mapper
WORKDIR /code/mapper

COPY requirements.txt /code/mapper
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . /code/mapper


# Section for PROD specific setup
FROM mbid-mapping-base as mbid-mapping-prod

# service start up scripts
COPY ./docker/consul-template.conf /etc/consul-template-mbid-mapping.conf
COPY ./docker/mapper.service /etc/service/mapper/run

# Add cron jobs
COPY docker/crontab /etc/cron.d/mapper
RUN chmod 0644 /etc/cron.d/mapper

COPY --chown=listenbrainz:listenbrainz requirements.txt /code/mapper
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY --chown=listenbrainz:listenbrainz . /code/mapper

# Ensure we use the right files and folders by removing duplicates
RUN rm -f /code/mapper/config.py /code/mapper/config.pyc
