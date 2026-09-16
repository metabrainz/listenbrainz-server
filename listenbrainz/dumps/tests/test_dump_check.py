from datetime import datetime
from unittest.mock import patch

from listenbrainz.dumps.check import _fetch_latest_file_info_from_ftp_dir


@patch("listenbrainz.dumps.check.FTP")
def test_fetch_latest_dump_normalizes_trailing_slash(mock_ftp):
    dump_names = [
        "listenbrainz-dump-122-20260615-030000-full",
        "listenbrainz-dump-123-20260701-030000-full/",
        "listenbrainz-dump-124-20260701-040000-db/",
    ]
    mock_ftp.return_value.retrlines.side_effect = (
        lambda command, callback: [callback(name) for name in dump_names]
    )

    dump_id, created = _fetch_latest_file_info_from_ftp_dir(
        "/pub/musicbrainz/listenbrainz/fullexport",
        True,
        "-full",
    )

    assert dump_id == 123
    assert created == datetime(2026, 7, 1, 3, 0)
