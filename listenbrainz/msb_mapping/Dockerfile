FROM metabrainz/python:3.7

RUN apt-get update && apt-get install -y ca-certificates && \
        pip install --upgrade pip

# service start up scripts
RUN mkdir -p /etc/service/mapper
COPY docker/mapper.service /etc/service/mapper/run
RUN chmod 755 /etc/service/mapper/run
COPY docker/consul-template.conf /etc/consul-template.conf

# Add cron jobs
COPY docker/crontab /etc/cron.d/mapper
RUN chmod 0644 /etc/cron.d/mapper

# I really don't think these are needed
#RUN touch /etc/service/cron/down
#COPY ./docker/rc.local /etc/rc.local

RUN mkdir -p /code/mapper
WORKDIR /code/mapper
COPY requirements.txt /code/mapper
RUN python -m pip install -r requirements.txt
COPY . /code/mapper
