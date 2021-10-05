import os
import logging

__version__ = '0.1'

DUMP_LICENSE_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                      'db', 'licenses', 'COPYING-PublicDomain')

_handler = logging.StreamHandler()
_handler.setLevel(logging.INFO)
_formatter = logging.Formatter("%(asctime)s %(name)-20s %(levelname)-8s %(message)s")
_handler.setFormatter(_formatter)

_logger = logging.getLogger("listenbrainz")
_logger.setLevel(logging.INFO)
_logger.addHandler(_handler)

