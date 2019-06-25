from datetime import datetime
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.testing import ServerTestCase

import listenbrainz.db.dump as db_dump


class DumpsViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def test_dump_get_404(self):
        r = self.client.get("/1/dump/get-info", query_string={"id": 1})
        self.assert404(r)

    def test_dump_get_200(self):
        now = datetime.now()
        dump_id = db_dump.add_dump_entry(int(now.strftime("%s")))
        r = self.client.get("/1/dump/get-info", query_string={"id": dump_id})
        self.assert200(r)
        self.assertDictEqual(r.json, {
            "id": dump_id,
            "timestamp": now.strftime("%Y%m%d-%H%M%S"),
        })

    def test_dump_get_400(self):
        r = self.client.get("/1/dump/get-info")
        self.assert400(r)

        r = self.client.get("/1/dump/get-info", query_string={"id": "pqrs"})
        self.assert400(r)
