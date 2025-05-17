import traceback
from datetime import datetime, timedelta
from ftplib import FTP
from typing import Optional

from brainzutils.mail import send_mail
from flask import current_app, render_template

from listenbrainz.webserver import create_app

MAIN_FTP_SERVER_URL = "ftp.eu.metabrainz.org"
FULLEXPORT_MAX_AGE = 17  # days
INCREMENTAL_MAX_AGE = 26  # hours
FEEDBACK_MAX_AGE = 8  # days


def _fetch_latest_file_info_from_ftp_dir(directory: str, has_id: bool):
    """
        Given a base FTP dir and whether the dump name contains an id, browses the MB FTP server to fetch
        the latest dump directory name and return it
    """

    latest_dump_id: Optional[int] = None
    latest_dt: Optional[datetime] = None

    def process_line(file):
        nonlocal latest_dump_id, latest_dt
        if file:
            if has_id:
                dump_id, dt = _parse_ftp_name_with_id(file)
            else:
                dump_id, dt = _parse_ftp_name_without_id(file)

            if latest_dt is None or dt > latest_dt:
                latest_dt = dt
                latest_dump_id = dump_id

    ftp = FTP(MAIN_FTP_SERVER_URL)
    ftp.login()
    ftp.cwd(directory)
    ftp.retrlines('NLST', process_line)

    return latest_dump_id, latest_dt


def _parse_ftp_name_with_id(name):
    """Parse a name like
        listenbrainz-dump-712-20220201-040003-full
    into its id (712), and a datetime.datetime object representing the datetime (2022-02-01 04:00:03)

    Returns:
        a tuple (id, datetime of file)
    """
    parts = name.split("-")
    if len(parts) != 6:
        raise ValueError("Filename '{}' expected to have 6 parts separated by -".format(name))
    _, _, dumpid, d, t, _ = parts
    return int(dumpid), datetime.strptime(d + t, "%Y%m%d%H%M%S")


def _parse_ftp_name_without_id(name):
    """Parse a name like
        listenbrainz-feedback-20220207-060003-full
    into an id (20220207-060003), and a datetime.datetime object representing the datetime (2022-02-07 06:00:03)

    Returns:
        a tuple (id, datetime of file)
    """
    parts = name.split("-")
    if len(parts) != 5:
        raise ValueError("Filename '{}' expected to have 5 parts separated by -".format(name))
    _, _, d, t, _ = parts
    return d + '-' + t, datetime.strptime(d + t, "%Y%m%d%H%M%S")


def check_ftp_dump_ages():
    """
        Fetch the FTP dir listing of the full and incremental dumps and check their ages. Send mail
        to the observability list in case the dumps are too old.
    """

    msg = ""
    try:
        dump_id, dt = _fetch_latest_file_info_from_ftp_dir('/pub/musicbrainz/listenbrainz/fullexport', True)
        age = datetime.now() - dt
        if age > timedelta(days=FULLEXPORT_MAX_AGE):
            msg = "Full dump %d is more than %d days old: %s\n" % (dump_id, FULLEXPORT_MAX_AGE, str(age))
            print(msg, end="")
        else:
            print("Full dump %s is %s old, good!" % (dump_id, str(age)))
    except Exception as err:
        msg = "Cannot fetch full dump age: %s\n\n%s" % (str(err), traceback.format_exc())

    try:
        dump_id, dt = _fetch_latest_file_info_from_ftp_dir('/pub/musicbrainz/listenbrainz/incremental', True)
        age = datetime.now() - dt
        if age > timedelta(hours=INCREMENTAL_MAX_AGE):
            msg = "Incremental dump %s is more than %s hours old: %s\n" % (dump_id, INCREMENTAL_MAX_AGE, str(age))
            print(msg, end="")
        else:
            print("Incremental dump %s is %s old, good!" % (dump_id, str(age)))
    except Exception as err:
        msg = "Cannot fetch incremental dump age: %s\n\n%s" % (str(err), traceback.format_exc())

    try:
        dump_id, dt = _fetch_latest_file_info_from_ftp_dir('/pub/musicbrainz/listenbrainz/spark', False)
        age = datetime.now() - dt
        if age > timedelta(days=FEEDBACK_MAX_AGE):
            msg = "Feedback dump %s is more than %s days old: %s\n" % (dump_id, FEEDBACK_MAX_AGE, str(age))
            print(msg, end="")
        else:
            print("Feedback dump %s is %s old, good!" % (dump_id, str(age)))
    except Exception as err:
        msg = "Cannot fetch feedback dump age: %s\n\n%s" % (str(err), traceback.format_exc())

    app = create_app()
    with app.app_context():
        if not current_app.config['TESTING'] and msg:
            send_mail(
                subject="ListenBrainz outdated dumps!",
                text=render_template('emails/data_dump_outdated.txt', msg=msg),
                recipients=['listenbrainz-exceptions@metabrainz.org'],
                from_name='ListenBrainz',
                from_addr='noreply@' + current_app.config['MAIL_FROM_DOMAIN']
            )
        elif msg:
            print(msg)
