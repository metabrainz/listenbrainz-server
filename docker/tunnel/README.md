This container is a complete hack to be able to view hadoop/spark HTTP interfaces without exposing those ports
to the world. To view the internal pages, do this:

1. Copy ssh key .pub files for all the users who should be able to create tunnels into the 'keys' directory.
2. run build.sh
3. Start the container with:

      docker run -p 2222:22 -it --name listenbrainz-tunnel --network spark-network metabrainz/listenbrainz-tunnel

4. Start a tunnel from the main leader login and tunnel into the container. If you want to be able to view
   port 8080 on the spark-master container, do:

      ssh -p 2222 -L 8080:spark-master:8080 root@localhost

5. Now you should be able to do:

      wget http://localhost:8080

   And it should load a page. If not, the setup isn't quite right.

6. Now from your own machine, you need to create another tunnel:

      ssh -L 8080:localhost:8080 robert@leader.listenbrainz.org

   If this worked, the HTTP pages should now appear on http://localhost:8080 on your local machine.
