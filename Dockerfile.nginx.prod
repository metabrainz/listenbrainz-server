FROM nginx:1.13.5

RUN apt-get update \
    && apt-get install -y --no-install-recommends 

WORKDIR /etc
COPY ./docker/prod/nginx/nginx.conf /etc/nginx/conf.d/default.conf
