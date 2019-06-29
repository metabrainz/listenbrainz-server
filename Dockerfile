FROM metabrainz/python:3.7 as listenbrainz-base

ARG deploy_env

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                       build-essential \
                       git \
                       libffi-dev \
                       libpq-dev \
                       libssl-dev \
                       pxz \
                       redis-tools \
                       rsync \
    && rm -rf /var/lib/apt/lists/*

# PostgreSQL client
RUN curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
ENV PG_MAJOR 9.5
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-$PG_MAJOR \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /code
WORKDIR /code

# MessyBrainz
RUN git clone https://github.com/metabrainz/messybrainz-server.git messybrainz
WORKDIR /code/messybrainz
RUN git checkout production
RUN pip3 install --no-cache-dir -r requirements.txt
RUN python3 setup.py install

RUN mkdir /code/listenbrainz
WORKDIR /code/listenbrainz

COPY requirements.txt /code/listenbrainz/
RUN pip3 install --no-cache-dir -r requirements.txt
RUN useradd --create-home --shell /bin/bash listenbrainz


# NOTE: The development image starts here
FROM listenbrainz-base as listenbrainz-dev
ARG deploy_env
COPY requirements_development.txt /code/listenbrainz
RUN pip3 install --no-cache-dir -r requirements_development.txt
RUN mkdir /code/listenbrainz/docs
COPY ./docs/requirements.txt /code/listenbrainz/docs
RUN pip3 install --no-cache-dir -r ./docs/requirements.txt
COPY . /code/listenbrainz


# NOTE: The production image starts here
FROM listenbrainz-base as listenbrainz-prod
ARG deploy_env

# Add cron jobs
ADD docker/crontab /etc/cron.d/lb-crontab
RUN chmod 0644 /etc/cron.d/lb-crontab && crontab -u listenbrainz /etc/cron.d/lb-crontab
RUN touch /var/log/stats.log /var/log/dump_create.log && chown listenbrainz:listenbrainz /var/log/stats.log /var/log/dump_create.log

# Make sure the cron service doesn't start automagically
# http://smarden.org/runit/runsv.8.html
RUN touch /etc/service/cron/down

# Consul Template service is already set up with the base image.
# Just need to copy the configuration.
COPY ./docker/consul-template.conf /etc/consul-template.conf
COPY ./docker/$deploy_env/uwsgi/uwsgi.service /etc/service/uwsgi/run
RUN chmod 755 /etc/service/uwsgi/run
COPY ./docker/$deploy_env/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
COPY ./docker/prod/uwsgi/uwsgi-api-compat.ini /etc/uwsgi/uwsgi-api-compat.ini

# Create directories for backups and FTP syncs
RUN mkdir /home/listenbrainz/backup /home/listenbrainz/ftp
RUN chown -R listenbrainz:listenbrainz /home/listenbrainz/backup /home/listenbrainz/ftp

# Now install our code, which may change frequently
COPY . /code/listenbrainz/

RUN mkdir /static
WORKDIR /static

# Compile static files
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
    apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json webpack.config.js ./listenbrainz/webserver/static /static/
RUN npm install && npm run build:prod && ./node_modules/less/bin/lessc --clean-css /static/css/main.less > /static/css/main.css && \
    rm -rf node_modules js/*.jsx *.json webpack.config.js && npm cache clean --force

WORKDIR /code/listenbrainz
RUN rm -rf ./listenbrainz/webserver/static/
RUN rm -f /code/listenbrainz/listenbrainz/config.py /code/listenbrainz/listenbrainz/config.pyc
