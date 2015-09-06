# listenbrainz-server
Server for the ListenBrainz project

## Development

Install ChefDK, then:

    $ kitchen create    # creates vm for first time
    $ kitchen converge  # provisions/installs from chef cookbooks
    $ kitchen login     # ssh in to vm

## Webserver

Install dependencies:

   $ pip install -r requirements.txt

Copy the file `config.py.sample` to `config.py` and edit the postgres
settings. For now you will need to allow your system user to connect
as the postgres admin user with no password.

Register for a musicbrainz application at 
https://musicbrainz.org/account/applications
Set the callback url to `http://<host>/login/musicbrainz/post`

Set up the database with

    $ python manage.py init_db

To run the server, run

    $ python manage.py runserver
