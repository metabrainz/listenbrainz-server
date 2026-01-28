#!/usr/bin/env python3

from collections import deque
import contextlib
import requests
import subprocess
import sys
from time import sleep
import os

from mapping.utils import log
import config

LINES_IN_LOG_SNIPPET = 500

FAILURE_REPORT_RETRIES = 20
FAILURE_REPORT_DELAY = 5  # in seconds


def post_telegram_message(msg):
    """ Post a message to the LB services Telegram channel """

    for retry in range(FAILURE_REPORT_RETRIES):
        r = requests.post(url="https://api.telegram.org/bot%s/sendMessage" % config.SERVICE_MONITOR_TELEGRAM_BOT_TOKEN,
                          data={
                              'chat_id': config.SERVICE_MONITOR_TELEGRAM_CHAT_ID,
                              'text': msg
                          })
        if r.status_code == 200:
            return

        if r.status_code in (400, 401, 403, 404, 429, 500):
            sleep(FAILURE_REPORT_DELAY)

    log("Failed to send error notification to the Telegram chat.\n")


def send_notification(script, return_code, stdout, stderr):
    """ Format the logs into a single text message and send it """

    msg = "script %s failed with error code %d:\n" % (script, return_code)
    msg += "STDOUT\n"
    msg += "\n".join(stdout)
    msg += "\n\n"
    if stderr:
        msg += "STDERR\n"
        msg += "\n".join(stderr)
        msg += "\n\n"

    post_telegram_message(msg)


def monitor(proc):
    """ Monitor a process by making the stdout/stderr non-blocking files. Continually read
        and save the stdout/stderr output, keeping only the last LINES_IN_LOG_SNIPPET lines
        of output of both. Once the called process terminates, return both stdout and stderr
        logs """

    newlines = ['\n', '\r\n', '\r']
    stdout = getattr(proc, "stdout")
    os.set_blocking(stdout.fileno(), False)
    stderr = getattr(proc, "stderr")
    os.set_blocking(stderr.fileno(), False)

    log_stdout = deque(maxlen=LINES_IN_LOG_SNIPPET)
    log_stderr = deque(maxlen=LINES_IN_LOG_SNIPPET)

    with contextlib.closing(stdout):
        with contextlib.closing(stderr):
            stdout_line = ""
            stderr_line = ""
            while True:
                if proc.poll() is not None:
                    return list(log_stdout), list(log_stderr)

                # Process stdout
                ch = stdout.read(1)
                if ch == "":
                    continue

                if ch in newlines:
                    sys.stdout.write(stdout_line + ch)
                    log_stdout.append(stdout_line)
                    stdout_line = ""
                    continue

                stdout_line += ch

                # Process stderr
                ch = stderr.read(1)
                if ch == "":
                    continue

                if ch in newlines:
                    sys.stdout.write(stderr_line + ch)
                    log_stderr.append(stderr_line)
                    stderr_line = ""
                    continue

                stderr_line += ch


def monitor_process(cmd):
    """ Call Popen to start monitoring a process, then monitor the proceess with the monitor method """

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    stdout, stderr = monitor(proc)
    return proc.returncode, stdout, stderr


def main():
    log("cron job starting")
    args = sys.argv[1:]
    if not args:
        log("Error: Must provide one program to execute.")
        sys.exit(-1)

    try:
        ret, stdout, stderr = monitor_process(args)
    except KeyboardInterrupt:
        sys.exit(-1)

    if ret == 0:
        # All went well, lets leave!
        sys.exit(0)

    # We did not exit successfully, so report an error
    send_notification(" ".join(sys.argv[1:]), ret, stdout, stderr)
    sys.exit(ret)


if __name__ == "__main__":
    main()
