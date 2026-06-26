import unittest

from flask import Flask

from listenbrainz.webserver import static_manager


class StaticManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["SERVER_NAME"] = "listenbrainz.example"
        static_manager.manifest_content = {}

    def tearDown(self):
        static_manager.manifest_content = {}

    def test_static_url_uses_flask_static_url_by_default(self):
        with self.app.test_request_context():
            self.assertEqual(
                static_manager.get_static_url("img/logo.svg"),
                "/static/img/logo.svg",
            )
            self.assertEqual(
                static_manager.get_static_url("img/logo.svg", external=True),
                "http://listenbrainz.example/static/img/logo.svg",
            )

    def test_static_url_uses_static_resources_url_when_configured(self):
        self.app.config["STATIC_RESOURCES_URL"] = "https://staticbrainz.org/listenbrainz/"

        with self.app.test_request_context():
            self.assertEqual(
                static_manager.get_static_url("img/logo.svg"),
                "https://staticbrainz.org/listenbrainz/img/logo.svg",
            )
            self.assertEqual(
                static_manager.get_static_url("/static/img/logo.svg"),
                "https://staticbrainz.org/listenbrainz/img/logo.svg",
            )

    def test_get_static_path_prefixes_manifest_paths(self):
        self.app.config["STATIC_RESOURCES_URL"] = "https://staticbrainz.org/listenbrainz"
        static_manager.manifest_content = {
            "main.scss": "/static/dist/main.abc123.css",
        }

        with self.app.test_request_context():
            self.assertEqual(
                static_manager.get_static_path("main.scss"),
                "https://staticbrainz.org/listenbrainz/dist/main.abc123.css",
            )

    def test_get_static_path_keeps_local_manifest_paths_by_default(self):
        static_manager.manifest_content = {
            "main.scss": "/static/dist/main.abc123.css",
        }

        with self.app.test_request_context():
            self.assertEqual(
                static_manager.get_static_path("main.scss"),
                "/static/dist/main.abc123.css",
            )
            self.assertEqual(
                static_manager.get_static_path("missing.css"),
                "/static/missing.css",
            )

    def test_get_static_path_prefixes_manifest_misses(self):
        self.app.config["STATIC_RESOURCES_URL"] = "https://staticbrainz.org/listenbrainz"

        with self.app.test_request_context():
            self.assertEqual(
                static_manager.get_static_path("missing.css"),
                "https://staticbrainz.org/listenbrainz/missing.css",
            )
