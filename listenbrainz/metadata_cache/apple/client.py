import requests
from requests import RequestException
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from listenbrainz.domain.apple import generate_developer_token


class Apple:

    def __init__(self):
        self.developer_token = generate_developer_token()
        self.retries = 5

    def _get_requests_session(self):
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()

        def _assert_status_hook(r, *args, **kwargs):
            r.raise_for_status()

        http.hooks["response"] = [_assert_status_hook]
        http.mount("https://", adapter)
        http.mount("http://", adapter)
        return http

    def get(self, url, params=None):
        with self._get_requests_session() as http:
            for _ in range(self.retries):
                response = http.get(url, params=params, headers={"Authorization": f"Bearer {self.developer_token}"})
                if response.status_code == 200:
                    return response.json()

                if response.status_code == 403:
                    self.developer_token = generate_developer_token()
            response.raise_for_status()
