import json
import time
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from lxml import etree


class AtomFeedsTestCase(ListenAPIIntegrationTestCase):
    def setUp(self):
        super(AtomFeedsTestCase, self).setUp()
        self.nsAtom = "{http://www.w3.org/2005/Atom}"

    def test_get_listens_invalid_params(self):
        """
        Check server sends 400 for invalid params.
        """
        listens_feed_url = self.custom_url_for(
            "atom.get_listens",
            user_name=self.user["musicbrainz_id"],
        )

        # invalid param
        response = self.client.get(listens_feed_url, query_string={"minutes": "-1"})
        self.assert400(response)
        response = self.client.get(
            listens_feed_url, query_string={"minutes": "10081"}
        )  # just above 1 week
        self.assert400(response)

        # invalid user
        invalid_user_url = self.custom_url_for("atom.get_listens", user_name="invalid")
        response = self.client.get(
            invalid_user_url,
        )
        self.assert404(response)

    def test_get_fresh_releases_invalid_params(self):
        """
        Check server sends 400 for invalid params.
        """
        fresh_releases_url = self.custom_url_for("atom.get_fresh_releases")
        response = self.client.get(fresh_releases_url, query_string={"days": "0"})
        self.assert400(response)
        response = self.client.get(fresh_releases_url, query_string={"days": "91"})
        self.assert400(response)

    def test_get_listens_feed_elements(self):
        """
        Check server sends valid listens feed.
        """
        with open(self.path_to_data_file("valid_single.json"), "r") as f:
            payload = json.load(f)

        ts = int(time.time())
        payload["payload"][0]["listened_at"] = ts
        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        url = self.custom_url_for(
            "atom.get_listens",
            user_name=self.user["musicbrainz_id"],
        )
        response = self.client.get(url)
        self.assert200(response)

        nsAtom = self.nsAtom
        xml_tree = etree.fromstring(response.data)
        feedId = xml_tree.find(f"{nsAtom}id")
        if feedId is None:
            self.fail("No id element found in feed")
        self.assertEqual(
            feedId.text,
            f"{self.custom_url_for('atom.get_listens', user_name=self.user['musicbrainz_id'], force_external=True)}",
        )

        entryId = xml_tree.find(f"{nsAtom}entry/{nsAtom}id")
        if entryId is None:
            self.fail("No id element found in feed")
        self.assertEqual(
            entryId.text,
            f"{self.custom_url_for('atom.get_listens', user_name=self.user['musicbrainz_id'], force_external=True)}/{ts}/{payload['payload'][0]['track_metadata']['track_name']}",
        )

    def test_get_listens_entry_order(self):
        """
        Check server sends listens feed with correct entry order.
        """
        with open(self.path_to_data_file("valid_single.json"), "r") as f:
            payload = json.load(f)

        # First listen
        ts1 = int(time.time())
        payload["payload"][0]["listened_at"] = ts1
        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # Second listen
        ts2 = int(time.time())
        payload["payload"][0]["listened_at"] = ts2
        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        url = self.custom_url_for(
            "atom.get_listens", user_name=self.user["musicbrainz_id"]
        )
        response = self.client.get(url, query_string={"interval": 1})
        self.assert200(response)

        nsAtom = self.nsAtom
        xml_tree = etree.fromstring(response.data)
        element = xml_tree.findall(f"{nsAtom}entry/{nsAtom}id")
        if element is None:
            self.fail("No id element found in feed")
        self.assertEqual(len(element), 2)
        self.assertEqual(
            element[0].text,
            f"{self.custom_url_for('atom.get_listens', user_name=self.user['musicbrainz_id'], force_external=True)}/{ts2}/{payload['payload'][0]['track_metadata']['track_name']}",
        )
        self.assertEqual(
            element[1].text,
            f"{self.custom_url_for('atom.get_listens', user_name=self.user['musicbrainz_id'], force_external=True)}/{ts1}/{payload['payload'][0]['track_metadata']['track_name']}",
        )
