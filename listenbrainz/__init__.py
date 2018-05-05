import os

__version__ = '0.1'

DUMP_LICENSE_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                      'db', 'licenses', 'COPYING-PublicDomain')


LAST_FM_FOUNDING_YEAR = 2002
INVALID_LISTENS_BIGQUERY_TABLE_NAME = 'before_2002'
