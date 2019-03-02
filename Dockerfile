FROM metabrainz/python:3.7

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                       build-essential \
                       redis-tools \
                       git \
                       libpq-dev \
                       libffi-dev \
                       pxz \
    && rm -rf /var/lib/apt/lists/*

# PostgreSQL client
RUN curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
ENV PG_MAJOR 9.5
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-$PG_MAJOR \
    && rm -rf /var/lib/apt/lists/*

# Node
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
    apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*

RUN mkdir /code
WORKDIR /code

# MessyBrainz
RUN git clone https://github.com/metabrainz/messybrainz-server.git messybrainz
WORKDIR /code/messybrainz
RUN pip3 install --no-cache-dir -r requirements.txt
RUN python3 setup.py install

RUN mkdir /code/listenbrainz
WORKDIR /code/listenbrainz

COPY requirements.txt /code/listenbrainz/
RUN pip3 install --no-cache-dir -r requirements.txt

# Now install our code, which may change frequently
COPY . /code/listenbrainz/

# create a user named listenbrainz for storing dump file backups
RUN useradd --create-home --shell /bin/bash listenbrainz

# setup a log dir
RUN mkdir /logs
RUN chown -R daemon:daemon /logs

# Add cron jobs
ADD docker/crontab /etc/cron.d/lb-crontab
RUN chmod 0644 /etc/cron.d/lb-crontab && crontab -u listenbrainz /etc/cron.d/lb-crontab
RUN touch /var/log/stats.log /var/log/dump_create.log && chown listenbrainz:listenbrainz /var/log/stats.log /var/log/dump_create.log

# Make sure the cron service doesn't start automagically
# http://smarden.org/runit/runsv.8.html
RUN touch /etc/service/cron/down
