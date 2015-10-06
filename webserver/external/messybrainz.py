from __future__ import absolute_import
import messybrainz
from messybrainz import exceptions


def init_db_connection(uri):
    messybrainz.db.init_db_engine(uri)


def submit_listens(listens):
    return messybrainz.submit_listens_and_sing_me_a_sweet_song(listens)
