import random
import requests
import threading
from config import BETA_URL


class StressTester(object):

    def __init__(self, listen_count, user_count):
        self.listen_count = listen_count
        self.user_count = user_count

    def user_submit(self, to_send, auth_token):
        data = {
            "listen_type": "single",
            "payload": [
                {
                    "listened_at": 1486449409,
                    "track_metadata": {
                        "artist_name": "Kanye West",
                        "track_name": "Fade",
                        "release_name": "The Life of Pablo"
                    }
                }
            ]
        }
        data['payload'][0]['listened_at'] = int(time.time())
        r = request.post(BETA_URL, headers=)

    def stress_test(self):
        for user in range(user_count):
            to_send = listen_count / user_count
            auth_token = str(uuid.uuid4())
            user_thread = threading.Thread(target=self.user_submit, args=(to_send, auth_token), daemon=False)
            user_thread.start()

