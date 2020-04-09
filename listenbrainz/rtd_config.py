DEBUG = False # set to False in production mode

SECRET_KEY = "CHANGE_ME"


# DATABASES

# Primary database
SQLALCHEMY_DATABASE_URI = "postgresql://listenbrainz:listenbrainz@db:5432/listenbrainz"
MESSYBRAINZ_SQLALCHEMY_DATABASE_URI = "postgresql://messybrainz:messybrainz@db:5432/messybrainz"

POSTGRES_ADMIN_URI="postgresql://postgres@db/template1"

SQLALCHEMY_TIMESCALE_URI = "postgresql://timescale_lb:timescale_lb@timescale/timescale_lb"
TIMESCALE_ADMIN_URI = "postgresql://postgres:postgres@timescale/template1"
TIMESCALE_ADMIN_LB_URI = "postgresql://postgres:postgres@timescale/timescale_lb"

# Other postgres configuration options
# Oldest listens which can be stored in the database, in days.
MAX_POSTGRES_LISTEN_HISTORY = "-1"
# Log Postgres queries if they execeed this time, in milliseconds.
PG_QUERY_TIMEOUT = "3000"
# Set to True to enable 'synchronous_commit' for Postgres. Default: False
PG_ASYNC_LISTEN_COMMIT = False


# Redis
REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_NAMESPACE = "listenbrainz"

# RabbitMQ
RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672
RABBITMQ_USERNAME = "guest"
RABBITMQ_PASSWORD = "guest"
RABBITMQ_VHOST = "/"
MAXIMUM_RABBITMQ_CONNECTIONS = 2

# RabbitMQ exchanges and queues
INCOMING_EXCHANGE = "incoming"
INCOMING_QUEUE = "incoming"
UNIQUE_EXCHANGE = "unique"
UNIQUE_QUEUE = "unique"
BIGQUERY_EXCHANGE = "bigquery"
BIGQUERY_QUEUE = "bigquery"

# MusicBrainz OAuth
MUSICBRAINZ_CLIENT_ID = "CLIENT_ID"
MUSICBRAINZ_CLIENT_SECRET = "CLIENT_SECRET"

# Lastfm API
LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"
LASTFM_API_KEY = "USE_LASTFM_API_KEY"

# BigQuery support
# Enable/disable support. If enabled, the Application Credentials must reside in
# bigquery-credentials.json in the top level directory.
WRITE_TO_BIGQUERY = False
BIGQUERY_PROJECT_ID = "listenbrainz"
BIGQUERY_DATASET_ID = "listenbrainz_test"
BIGQUERY_TABLE_ID = "listen"

# Stats
STATS_ENTITY_LIMIT = 100 # the number of entities to calculate at max with BQ
STATS_CALCULATION_LOGIN_TIME = 30 # users must have logged in to LB in the past 30 days for stats to be calculated
STATS_CALCULATION_INTERVAL = 7 # stats are calculated every 7 days


# Max time in seconds after which the playing_now stream will expire.
PLAYING_NOW_MAX_DURATION = 10 * 60

# LOGGING

#LOG_FILE_ENABLED = True
#LOG_FILE = "./listenbrainz.log"

#LOG_EMAIL_ENABLED = True
#LOG_EMAIL_TOPIC = "ListenBrainz Webserver Failure"
#LOG_EMAIL_RECIPIENTS = []  # List of email addresses (strings)

#LOG_SENTRY_ENABLED = True
#SENTRY_DSN = ""


# MISCELLANEOUS

# Set to True if Less should be compiled in browser. Set to False if styling is pre-compiled.
COMPILE_LESS = True

# MAX file size to be allowed for the lastfm-backup import, default is infinite
# Size is in bytes
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Specify the upload folder where all the lastfm-backup will be stored
# The path must be absolute path
UPLOAD_FOLDER = "/tmp/lastfm-backup-upload"

API_URL = 'https://api.listenbrainz.org'
LASTFM_PROXY_URL = 'http://0.0.0.0:8080/'
MUSICBRAINZ_OAUTH_URL = 'https://musicbrainz.org/oauth2/userinfo'
SPOTIFY_CLIENT_ID = ''
SPOTIFY_CLIENT_SECRET = ''

ADMINS = ['iliekcomputers']
