#!/bin/bash

cd /vagrant
docker-compose -f docker/docker-compose.prod.yml build && docker-compose -f docker/docker-compose.prod.yml up
