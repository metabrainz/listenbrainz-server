DEBUG = False # set to False in production mode

SECRET_KEY = "CHANGE_ME"


# DATABASES

# Primary database
SQLALCHEMY_DATABASE_URI = "postgresql://messybrainz:messybrainz@db:5432/messybrainz"

# Database for testing
TEST_SQLALCHEMY_DATABASE_URI = "postgresql://msb_test:msb_test@db:5432/msb_test"

# Admin database
POSTGRES_ADMIN_URI = "postgresql://postgres:postgres@db/postgres"



# MUSICBRAINZ

MUSICBRAINZ_USERAGENT = "messybrainz-server"
MUSICBRAINZ_HOSTNAME = None


# CACHE
REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_NAMESPACE = "messybrainz"


# LOGGING

#LOG_FILE_ENABLED = True
#LOG_FILE = "./messybrainz.log"

#LOG_EMAIL_ENABLED = True
#LOG_EMAIL_TOPIC = "MessyBrainz Webserver Failure"
#LOG_EMAIL_RECIPIENTS = []  # List of email addresses (strings)

#LOG_SENTRY_ENABLED = True
#SENTRY_DSN = ""


# MISCELLANEOUS

#BEHIND_GATEWAY = True
#REMOTE_ADDR_HEADER = "X-MB-Remote-Addr"

IP_FILTER_ON = False
IP_WHITELIST = [
    #'127.0.0.1',
]

# Mail server
# These variables need to be defined if you enabled log emails.
#SMTP_SERVER = "localhost"
#SMTP_PORT = 25
#MAIL_FROM_DOMAIN = "messybrainz.org"

# Set to True if Less should be compiled in browser. Set to False if styling is pre-compiled.
COMPILE_LESS = True

FILE_STORAGE_DIR = "./files"
