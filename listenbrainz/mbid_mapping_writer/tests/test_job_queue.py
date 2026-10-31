from datetime import datetime, timedelta, timezone

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
        self.job_queue = MappingJobQueue(self.app)
        # the constructor starts loading legacy listens, wait for it before setting up the data
        self.job_queue.legacy_load_thread.join()
        self.job_queue.legacy_load_thread = None
        while not self.job_queue.queue.empty():
            self.job_queue.queue.get()

    def test_add_legacy_listens_to_queue(self):
        """ Test that legacy listens in the time window that are not mapped to a recording are queued once """
        unmapped_msid, mapped_msid, no_match_msid, outside_msid = messybrainz.insert_all_in_transaction(
            self.listens_conn,
            [{"title": title, "artist": "Portishead"} for title in ["Roads", "Glory Box", "Sour Times", "Wandering Star"]]
        )
        index_date = datetime(2021, 1, 10, tzinfo=timezone.utc)
        in_window = index_date - timedelta(days=1)
        rows = [
            (in_window, in_window, self.user["id"], unmapped_msid, '{}'),
            (in_window - timedelta(hours=1), in_window, self.user["id"], unmapped_msid, '{}'),
            (in_window, in_window, self.user["id"], mapped_msid, '{}'),
            (in_window, in_window, self.user["id"], no_match_msid, '{}'),
            (index_date - LEGACY_LISTENS_LOAD_WINDOW, in_window, self.user["id"], outside_msid, '{}'),
        ]
        listens_db.insert(rows)
        self.listens_conn.execute(text("""
            INSERT INTO mapping.mbid_mapping (recording_msid, recording_mbid, match_type, check_again)
                 VALUES (:mapped_msid, '2f3d422f-8890-41a1-9762-fbe16f107c31', 'exact_match', NULL)
                      , (:no_match_msid, NULL, 'no_match', NOW() + INTERVAL '1 day')
        """), {"mapped_msid": mapped_msid, "no_match_msid": no_match_msid})
        self.listens_conn.commit()

        self.job_queue.legacy_listens_index_date = index_date
        self.job_queue.add_legacy_listens_to_queue()

        queued = []
        while not self.job_queue.queue.empty():
            job = self.job_queue.queue.get()
            self.assertEqual(job.priority, LEGACY_LISTEN)
            queued.extend(str(item["recording_msid"]) for item in job.item)
        self.assertCountEqual(queued, [unmapped_msid, no_match_msid])
        self.assertEqual(self.job_queue.legacy_listens_index_date, index_date - LEGACY_LISTENS_LOAD_WINDOW)
