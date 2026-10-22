FROM docker.io/metabrainz/python:3.13-20261022 AS mbid-mapping-base

RUN apt-get update && apt-get install -y ca-certificates python3-pip netpbm git \
    && pip install --no-cache-dir --no-deps --upgrade "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"

RUN groupadd --gid 901 listenbrainz
RUN useradd --create-home --shell /bin/bash --uid 901 --gid 901 listenbrainz

RUN mkdir -p /code/mapper && chown listenbrainz:listenbrainz /code/mapper
WORKDIR /code/mapper

COPY requirements.txt /code/mapper
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . /code/mapper


# Section for PROD specific setup
FROM mbid-mapping-base AS mbid-mapping-prod

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
