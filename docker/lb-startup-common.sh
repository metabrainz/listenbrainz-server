# Common functions used in run-lb-command and run .finish files

function log() {
    printf "%(%Y-%m-%d %H:%M:%S %Z)T "
    echo "$@"
}

function generate_message() {
  message="$service terminated. "
  if [ $# -gt 0 ] && [ $1 -eq 0 ]; then
    message+="Exit status 0 (consul triggered reload or service was stopped)"
  elif [ $# -gt 0 ] && [ $1 -eq 22 ]; then
    message+="Exit status 22 (uwsgi failed to start app, check container logs)"
  elif [ $# -gt 0 ]; then
    message+="Exit status $1"
  else
    message+="unexpectedly called with no arguments"
  fi
}

function send_sentry_message() {
  # Send a message to sentry
  # Requires these arguments:
  #   project: the name of the project that is running (e.g. 'listenbrainz')
  #   $message: the message to report
  #   $SENTRY_SERVICE_ERROR_DSN: the DSN to report errors to
  if [ -z "${SENTRY_SERVICE_ERROR_DSN}" ]; then
    log "SENTRY_SERVICE_ERROR_DSN environment variable isn't set, not logging"
  elif ! command -v sentry-cli ; then
    log "Cannot find sentry-cli, not logging"
  else
    SENTRY_DSN="${SENTRY_SERVICE_ERROR_DSN}" sentry-cli send-event -f $(uuidgen) -E "$project" -m "$message"
  fi
}