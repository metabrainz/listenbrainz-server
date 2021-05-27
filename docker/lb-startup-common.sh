# Common functions used in run-lb-command and run .finish files

function log() {
    printf "%(%Y-%m-%d %H:%M:%S %Z)T "
    echo "$@"
}

function generate_message() {
  # Generate a message indicating that a service has terminated.
  # If the exit code is known, an additional message is added indicating what happened.
  # arguments:
  #   $1 service name
  #   $2 exit code of the service
  # return:
  #   sets variable $message with the value of the generated message
  message="$1 terminated. "
  if [ $# -gt 1 ] && [ $2 -eq 0 ]; then
    message+="Exit status 0 (consul triggered reload or service was stopped)"
  elif [ $# -gt 1 ] && [ $2 -eq 15 ]; then
    message+="Exit status 15 (consul-template failed to start up)"
  elif [ $# -gt 1 ] && [ $2 -eq 22 ]; then
    message+="Exit status 22 (uwsgi failed to start app, check container logs)"
  elif [ $# -gt 1 ]; then
    message+="Exit status $2"
  else
    message+="unexpectedly called with no arguments"
  fi
}

function send_sentry_message() {
  # Send a message to sentry
  # required globals:
  #   $SENTRY_SERVICE_ERROR_DSN: the DSN to report errors to
  #   $SENTRY_SERVICE_ERROR_ENVIRONMENT: the name of this project, used to set a sentry environment
  #   $DEPLOY_ENV: the deploy environment, used to set a sentry environment
  # arguments:
  #   $1: the message to report

  if [ -z "${SENTRY_SERVICE_ERROR_DSN}" ]; then
    log "SENTRY_SERVICE_ERROR_DSN environment variable isn't set, not logging"
  elif ! type -p sentry-cli &>/dev/null; then
    log "Cannot find sentry-cli, not logging"
  else
    SENTRY_DSN="${SENTRY_SERVICE_ERROR_DSN}" sentry-cli send-event -f $(uuid) \
      -E "${SENTRY_SERVICE_ERROR_ENVIRONMENT}-${DEPLOY_ENV}" -m "$@"
  fi
}