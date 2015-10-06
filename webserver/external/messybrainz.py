from __future__ import absolute_import
import os

try:
    # Should be able to continue if messybrainz package is unavailable during
    # documentation generation (we don't need it in this case).
    import messybrainz
    from messybrainz import exceptions
except ImportError:
    on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
    if not on_rtd:
        raise


def init_db_connection(uri):
    messybrainz.db.init_db_engine(uri)


def submit_listens(listens):
    return messybrainz.submit_listens_and_sing_me_a_sweet_song(listens)
