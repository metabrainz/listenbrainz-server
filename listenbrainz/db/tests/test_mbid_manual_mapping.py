import sqlalchemy.exc

import listenbrainz.db.mbid_manual_mapping as db_mbid_manual_mapping

from listenbrainz.db.model.mbid_manual_mapping import MbidManualMapping
from listenbrainz.db.testing import TimescaleTestCase


class MbidManualMappingDatabaseTestCase(TimescaleTestCase):

    def test_add_get_mapping(self):
        """Add and get a mapping"""
        msid = "597fa2f2-8cf4-4566-a307-dbfb5aa35ec4"
        mbid = "c8d63620-ced3-4abf-84f8-85457ce798c6"
        user_id = 1

        mapping = MbidManualMapping(recording_msid=msid, recording_mbid=mbid, user_id=user_id)
        db_mbid_manual_mapping.create_mbid_manual_mapping(self.ts_conn, mapping)
        
        new_mapping = db_mbid_manual_mapping.get_mbid_manual_mapping(self.ts_conn, msid, user_id)
        assert new_mapping.recording_mbid == mapping.recording_mbid
        assert new_mapping.recording_msid == mapping.recording_msid
        assert new_mapping.user_id == mapping.user_id

    def test_cant_add_same_mapping_twice(self):
        """Try and add the same mapping by the same user twice, it gets updated"""
        msid = "597fa2f2-8cf4-4566-a307-dbfb5aa35ec4"
        mbid1 = "c8d63620-ced3-4abf-84f8-85457ce798c6"
        mbid2 = "cb24f4bb-3ecf-44c7-bba9-5241faac3ce8"
        user_id = 1

        mapping1 = MbidManualMapping(recording_msid=msid, recording_mbid=mbid1, user_id=user_id)
        db_mbid_manual_mapping.create_mbid_manual_mapping(self.ts_conn, mapping1)
        new_mapping = db_mbid_manual_mapping.get_mbid_manual_mapping(self.ts_conn, msid, user_id)
        assert new_mapping.recording_mbid == mbid1

        mapping2 = MbidManualMapping(recording_msid=msid, recording_mbid=mbid2, user_id=user_id)
        db_mbid_manual_mapping.create_mbid_manual_mapping(self.ts_conn, mapping2)

        new_mapping = db_mbid_manual_mapping.get_mbid_manual_mapping(self.ts_conn, msid, user_id)
        assert new_mapping.recording_mbid == mbid2

    def test_add_mapping_different_users(self):
        """Add a mapping for the same msid by different users and get them"""
        msid = "597fa2f2-8cf4-4566-a307-dbfb5aa35ec4"
        mbid1 = "c8d63620-ced3-4abf-84f8-85457ce798c6"
        mbid2 = "cb24f4bb-3ecf-44c7-bba9-5241faac3ce8"
        user_id1 = 1
        user_id2 = 2

        mapping1 = MbidManualMapping(recording_msid=msid, recording_mbid=mbid1, user_id=user_id1)
        db_mbid_manual_mapping.create_mbid_manual_mapping(self.ts_conn, mapping1)

        mapping2 = MbidManualMapping(recording_msid=msid, recording_mbid=mbid2, user_id=user_id2)
        db_mbid_manual_mapping.create_mbid_manual_mapping(self.ts_conn, mapping2)

        new_mappings = db_mbid_manual_mapping.get_mbid_manual_mappings(self.ts_conn, msid)
        assert len(new_mappings) == 2
