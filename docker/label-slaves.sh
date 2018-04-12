#!/bin/bash

for id in `docker node ls -q -f "role=worker"`; do
    docker node update --label-add type=slave $id
done
