# listenbrainz-server
Server for the ListenBrainz project

## Development

Install ChefDK, then:

    $ kitchen create    # creates vm for first time
    $ kitchen converge  # provisions/installs from chef cookbooks
    $ kitchen login     # ssh in to vm
