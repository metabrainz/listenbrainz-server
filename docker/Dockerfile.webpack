FROM node:10.15-alpine

RUN mkdir /code
WORKDIR /code

COPY package.json package-lock.json webpack.config.js /code/
RUN npm install
