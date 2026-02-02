from datetime import datetime, timedelta

import listenbrainz.db.user as db_user
from listenbrainz.db import do_not_recommend

from listenbrainz.tests.integration import IntegrationTestCase


class DoNotRecommendAPITestCase(IntegrationTestCase):

    def setUp(self):
        super(DoNotRecommendAPITestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, "test_user_1")

        self.items = [
            {
                "entity": "release_group",
                "entity_mbid": "1fa0a3e5-6e9e-4a51-b994-02f0367a7b10",
                "until": int((datetime.now() + timedelta(days=1)).timestamp())
            },
            {
                "entity": "recording",
                "entity_mbid": "c2d6beba-81f9-43cd-871d-de005aa25ba8",
                "until": int((datetime.now() + timedelta(days=2)).timestamp())
            },
            {
                "entity": "release",
                "entity_mbid": "c7cd4f1c-30cc-4ae4-887c-7a33674e6153",
                "until": int((datetime.now() + timedelta(days=3)).timestamp())
            },
            {
                "entity": "artist",
                "entity_mbid": "c11b38ea-4997-415d-b1d9-11338806ad98",
                "until": int((datetime.now() + timedelta(days=4)).timestamp())
            }
        ]

    def insert_test_data(self, limit: int = None):
        if limit is None:
            limit = len(self.items)

        for item in self.items[:limit]:
            do_not_recommend.insert(self.db_conn, self.user["id"], item["entity"], item["entity_mbid"], item["until"])

    def _check_response(self, response, expected, offset=0, total_count=None):
        self.assert200(response)
        data = response.json
        self.assertEqual(data["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(data["count"], len(expected))
        self.assertEqual(data["offset"], offset)
        self.assertEqual(data["total_count"], total_count or len(expected))
        self.assertEqual(data["user_id"], self.user["musicbrainz_id"])
        for expected, received in zip(expected, data["results"]):
            self.assertEqual(expected["entity"], received["entity"])
            self.assertEqual(expected["entity_mbid"], received["entity_mbid"])
            self.assertEqual(expected["until"], received["until"])

    def test_get_do_not_recommends(self):
        self.insert_test_data()
        url = self.custom_url_for("do_not_recommend_api_v1.get_do_not_recommends",
                                  user_name=self.user["musicbrainz_id"])
        response = self.client.get(url)
        self._check_response(response, self.items)

    def test_delete_do_not_recommend(self):
        self.insert_test_data()
        url = self.custom_url_for("do_not_recommend_api_v1.delete_do_not_recommend",
                                  user_name=self.user["musicbrainz_id"])
        response = self.client.post(
            url,
            json={"entity": self.items[3]["entity"], "entity_mbid": self.items[3]["entity_mbid"]},
            headers={"Authorization": f'Token {self.user["auth_token"]}'}
        )
        self.assert200(response)

        response = self.client.get(
            self.custom_url_for("do_not_recommend_api_v1.get_do_not_recommends", user_name=self.user["musicbrainz_id"]))
        self._check_response(response, self.items[:3])

    def test_add_do_not_recommend(self):
        url = self.custom_url_for("do_not_recommend_api_v1.add_do_not_recommend", user_name=self.user["musicbrainz_id"])
        response = self.client.post(
            url,
            json=self.items[0],
            headers={"Authorization": f'Token {self.user["auth_token"]}'}
        )
        self.assert200(response)

        new_item = {"entity": self.items[1]["entity"], "entity_mbid": self.items[1]["entity_mbid"]}
        response = self.client.post(
            url,
            json=new_item,
            headers={"Authorization": f'Token {self.user["auth_token"]}'}
        )
        self.assert200(response)
        new_item["until"] = None

        response = self.client.get(
            self.custom_url_for("do_not_recommend_api_v1.get_do_not_recommends", user_name=self.user["musicbrainz_id"]))
        self._check_response(response, [self.items[0], new_item])

    def test_invalid_username(self):
        user_name = " -- invalid username -- "
        response = self.client.get(
            self.custom_url_for("do_not_recommend_api_v1.get_do_not_recommends", user_name=user_name))
        self.assert404(response)
        self.assertEqual(response.json["code"], 404)

    def test_unauthorized(self):
        response = self.client.post(self.custom_url_for("do_not_recommend_api_v1.delete_do_not_recommend",
                                                        user_name=self.user["musicbrainz_id"]))
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

        response = self.client.post(
            self.custom_url_for("do_not_recommend_api_v1.add_do_not_recommend", user_name=self.user["musicbrainz_id"]))
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

    def test_invalid_entity(self):
        invalid_entity_error = "Value 'label' for entity key is invalid"
        urls = [
            self.custom_url_for("do_not_recommend_api_v1.delete_do_not_recommend",
                                user_name=self.user["musicbrainz_id"]),
            self.custom_url_for("do_not_recommend_api_v1.add_do_not_recommend", user_name=self.user["musicbrainz_id"])
        ]
        for url in urls:
            response = self.client.post(
                url,
                json={"entity": "label", "entity_mbid": self.items[3]["entity_mbid"], "until": 1},
                headers={"Authorization": f'Token {self.user["auth_token"]}'}
            )
            self.assert400(response)
            self.assertEqual(response.json["code"], 400)
            self.assertTrue(response.json["error"].startswith(invalid_entity_error))

    def test_invalid_entity_mbid(self):
        invalid_entity_mbid_error = "Value 'foobar' for entity_mbid key is not a valid uuid"
        urls = [
            self.custom_url_for("do_not_recommend_api_v1.delete_do_not_recommend",
                                user_name=self.user["musicbrainz_id"]),
            self.custom_url_for("do_not_recommend_api_v1.add_do_not_recommend", user_name=self.user["musicbrainz_id"])
        ]
        for url in urls:
            response = self.client.post(
                url,
                json={"entity": "artist", "entity_mbid": "foobar", "until": 1},
                headers={"Authorization": f'Token {self.user["auth_token"]}'}
            )
            self.assert400(response)
            self.assertEqual(response.json["code"], 400)
            self.assertTrue(response.json["error"].startswith(invalid_entity_mbid_error))

    def test_invalid_until(self):
        url = self.custom_url_for("do_not_recommend_api_v1.add_do_not_recommend", user_name=self.user["musicbrainz_id"])

        response = self.client.post(
            url,
            json={"entity": self.items[0]["entity"], "entity_mbid": self.items[0]["entity_mbid"], "until": "foo"},
            headers={"Authorization": f'Token {self.user["auth_token"]}'}
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(
            response.json["error"],
            "Value 'foo' for until key is invalid. 'until' should be a positive integer"
        )

        response = self.client.post(
            url,
            json={"entity": self.items[0]["entity"], "entity_mbid": self.items[0]["entity_mbid"], "until": -10},
            headers={"Authorization": f'Token {self.user["auth_token"]}'}
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(
            response.json["error"],
            "Value '-10' for until key is invalid. 'until' should be a positive integer"
        )

    def test_count_offset_get(self):
        self.insert_test_data()
        response = self.client.get(
            self.custom_url_for("do_not_recommend_api_v1.get_do_not_recommends", user_name=self.user["musicbrainz_id"],
                                count=2)
        )
        self._check_response(response, self.items[:2], total_count=4)
        response = self.client.get(
            self.custom_url_for("do_not_recommend_api_v1.get_do_not_recommends", user_name=self.user["musicbrainz_id"],
                                offset=2)
        )
        self._check_response(response, self.items[2:], total_count=4, offset=2)
