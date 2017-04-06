from __future__ import print_function
import random
import requests
import threading
import uuid
import argparse
import string
import json

BETA_URL = 'http://0.0.0.0:3031'

TIMESTAMP_LOW = 946684800   # unix timestamp of 01/01/2000
TIMESTAMP_HIGH = 1491004800 # unix timestamp of 01/04/2017


class StressTester(object):

    def __init__(self, listen_count, user_count):
        self.listen_count = listen_count
        self.user_count = user_count

    def random_timestamp(self):
        """
        Returns a random timestamp between TIMESTAMP_LOW and TIMESTAMP_HIGH
        """
        return int(TIMESTAMP_LOW + (TIMESTAMP_HIGH - TIMESTAMP_HIGH) * random.random())

    def random_string(self):
        """
        Returns a random string containing uppercase and lowercase ascii characters and digits
        """
        # random length b/w 1 and 50
        l = random.randint(1, 50)
        s = ''
        for _ in range(l):
            s += random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
        return s

    def random_listen(self):
        """
        Generates random listen data
        """

        payload = {
            'listen_type': 'single',
            'payload': [{
                'listened_at': self.random_timestamp(),
                'track_metadata': {
                    'artist_name': self.random_string(),
                    'track_name': self.random_string(),
                    'release_name': self.random_string(),
                    'additional_info': {
                        'random_data': self.random_string(),
                    }
                }
            }]
        }

        return payload

    def user_submit(self, to_send, auth_token):
        accepted = 0
        for _ in xrange(to_send):
            send_url = '{}/1/submit-listens'.format(BETA_URL)
            data = self.random_listen()
            response = requests.post(
                send_url,
                headers={'Authorization': 'Token {}'.format(auth_token)},
                data = json.dumps(data),
            )
            if response.status_code == 200:
                accepted += 1
        print("For user with auth_token {}, number of listens accepted: {}".format(auth_token, accepted))

    def stress_test(self):
        for user in range(self.user_count):
            to_send = self.listen_count / self.user_count
            auth_token = str(uuid.uuid4())
            user_thread = threading.Thread(target=self.user_submit, args=(to_send, auth_token))
            user_thread.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--listencount", dest="listen_count", type=int, help="specify the number of listens to send while testing")
    parser.add_argument("-u", "--usercount", dest="user_count", type=int, help="specify the number of users to spread the listens over")
    args = parser.parse_args()
    if args.listen_count and args.user_count:
        st = StressTester(args.listen_count, args.user_count)
        st.stress_test()
    else:
        print("Please provide all options required, see -h for help")
