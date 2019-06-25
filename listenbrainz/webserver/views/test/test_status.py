from datetime import datetime, timedelta
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.testing import ServerTestCase

import listenbrainz.db.dump as db_dump


class StatusViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def test_dump_get_404(self):
        r = self.client.get("/1/status/get-dump-info", query_string={"id": 1})
        self.assert404(r)

    def test_dump_get_200(self):
        t0 = datetime.now()
        dump_id = db_dump.add_dump_entry(int(t0.strftime("%s")))
        r = self.client.get("/1/status/get-dump-info", query_string={"id": dump_id})
        self.assert200(r)
        self.assertDictEqual(r.json, {
            "id": dump_id,
            "timestamp": t0.strftime("%Y%m%d-%H%M%S"),
        })

        # should return the latest dump if no dump ID passed
        t1 = t0 + timedelta(seconds=1)
        dump_id_1 = db_dump.add_dump_entry(int(t1.strftime("%s")))
        r = self.client.get("/1/status/get-dump-info")
        self.assert200(r)
        self.assertDictEqual(r.json, {
            "id": dump_id_1,
            "timestamp": t1.strftime("%Y%m%d-%H%M%S"),
        })

    def test_dump_get_400(self):
        r = self.client.get("/1/status/get-dump-info", query_string={"id": "pqrs"})
        self.assert400(r)
