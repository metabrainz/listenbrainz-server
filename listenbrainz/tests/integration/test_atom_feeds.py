import json
import time
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from lxml import etree


class AtomFeedsTestCase(ListenAPIIntegrationTestCase):
    def test_user_listens_feed(self):
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
            "atom.get_listens", user_name=self.user["musicbrainz_id"]
        )
        response = self.client.get(url, query_string={"interval": 1})
        self.assert200(response)

        xml_tree = etree.fromstring(response.data)
        nsAtom = "{http://www.w3.org/2005/Atom}"
        element = xml_tree.find(f"{nsAtom}id")
        if element is None:
            self.fail("No id element found in feed")
        self.assertEqual(element.text, f"https://listenbrainz.org/user/{self.user['musicbrainz_id']}")
