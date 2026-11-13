from datetime import datetime, timezone, timedelta

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz import messybrainz
from listenbrainz.db import listens as listens_db
from listenbrainz.mbid_mapping_writer.job_queue import MappingJobQueue, LEGACY_LISTEN, LEGACY_LISTENS_LOAD_WINDOW
from listenbrainz.tests.integration import NonAPIIntegrationTestCase


class TestMappingJobQueue(NonAPIIntegrationTestCase):

    def setUp(self):
        super(TestMappingJobQueue, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, "test")
        self.other_user = db_user.get_or_create(self.db_conn, 2, "other")
        self.job_queue = MappingJobQueue(self.app)
        # the constructor starts loading legacy listens, wait for it before setting up the data
        self.job_queue.legacy_load_thread.join()
        self.job_queue.legacy_load_thread = None
        self._drain_queue()

    def _drain_queue(self):
        queued = []
        while not self.job_queue.queue.empty():
            job = self.job_queue.queue.get()
            self.assertEqual(job.priority, LEGACY_LISTEN)
            queued.extend(str(item["recording_msid"]) for item in job.item)
        return queued

    def test_add_legacy_listens_to_queue(self):
        """ Test that legacy listens that are not mapped to a recording are queued once per window of created
            time they are in, going back one window at a time, until the oldest listen is done """
        unmapped_msid, mapped_msid, no_match_msid, other_msid = messybrainz.insert_all_in_transaction(
            self.listens_conn,
            [{"title": title, "artist": "Portishead"} for title in ["Roads", "Glory Box", "Sour Times", "Wandering Star"]]
        )
        ts = datetime(2021, 1, 10, tzinfo=timezone.utc)
        older = ts - LEGACY_LISTENS_LOAD_WINDOW * 2
        rows = [
            (ts, ts, self.user["id"], unmapped_msid, '{}'),
            (ts.replace(hour=1), ts, self.user["id"], unmapped_msid, '{}'),
            (older, older, self.user["id"], unmapped_msid, '{}'),
            (ts, ts, self.user["id"], mapped_msid, '{}'),
            (ts, ts, self.user["id"], no_match_msid, '{}'),
            (older, older, self.other_user["id"], other_msid, '{}'),
        ]
        listens_db.insert(rows)
        self.listens_conn.execute(text("""
            INSERT INTO mapping.mbid_mapping (recording_msid, recording_mbid, match_type, check_again)
                 VALUES (:mapped_msid, '2f3d422f-8890-41a1-9762-fbe16f107c31', 'exact_match', NULL)
                      , (:no_match_msid, NULL, 'no_match', NOW() + INTERVAL '1 day')
        """), {"mapped_msid": mapped_msid, "no_match_msid": no_match_msid})
        self.listens_conn.commit()

        self.job_queue.legacy_listens_index_date = ts + timedelta(days=1)
        self.job_queue.legacy_next_run = 0
        queued = []
        passes = 0
        while not self.job_queue.legacy_next_run:
            self.job_queue.add_legacy_listens_to_queue()
            queued.extend(self._drain_queue())
            passes += 1
            self.assertLess(passes, 10)
        # the listens of the unmapped msid are in two windows, the listens in the same window are queued once
        self.assertCountEqual(queued, [unmapped_msid, unmapped_msid, no_match_msid, other_msid])
        # done, so it starts again from now next time
        self.assertGreater(self.job_queue.legacy_listens_index_date, ts + timedelta(days=1))
