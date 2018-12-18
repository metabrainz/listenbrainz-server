To run the gateway:

cp ~/.ssh/id_rsa.pub .
buid.sh
docker rm -f listenbrainz-gateway && docker run -p 2222:22 -it --name listenbrainz-gateway --network spark-network metabrainz/listenbrainz-gateway
ssh -p 2222 -L 9864:localhost:9864 root@localhost
