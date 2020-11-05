FROM ubuntu:20.10

RUN apt-get update && apt-get install -y ca-certificates python3-pip && \
        pip install --upgrade pip

RUN groupadd --gid 901 listenbrainz
RUN useradd --create-home --shell /bin/bash --uid 901 --gid 901 listenbrainz

RUN mkdir -p /code/mapper && chown listenbrainz:listenbrainz /code/mapper
WORKDIR /code/mapper

COPY requirements.txt /code/mapper
RUN python3 -m pip install --no-cache-dir -r requirements.txt
COPY . /code/mapper
