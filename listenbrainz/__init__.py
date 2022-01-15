import os
import logging

__version__ = '0.1'

DUMP_LICENSE_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                      'db', 'licenses', 'COPYING-PublicDomain')

_handler = logging.StreamHandler()
_formatter = logging.Formatter("%(asctime)s %(name)-20s %(levelname)-8s %(message)s")
_handler.setFormatter(_formatter)

_logger = logging.getLogger("listenbrainz")
# This level is set to DEBUG in listenbrainz.webserver.gen_app if Flask DEBUG=True
_logger.setLevel(logging.INFO)
