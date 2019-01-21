from brainzutils.mail import send_mail
from listenbrainz.spotify_updater.spotify_read_listens import notify_error
from listenbrainz.webserver import create_app

import listenbrainz.db.user as db_user

if __name__ == '__main__':
    with create_app().app_context():
        user = db_user.get_by_mb_id('iliekcomputers')
        notify_error(user['musicbrainz_row_id'], "This is a test errror")

