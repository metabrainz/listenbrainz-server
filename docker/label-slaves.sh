#!/bin/bash

for id in `docker node ls -q -f "role=worker"`; do
    docker node --label-add type=slave $id
done
