from __future__ import print_function
import random
import requests
import threading
import uuid
import argparse
import string
import json
import time

LB_URL = 'http://10.1.1.4'

TIMESTAMP_LOW = 946684800   # unix timestamp of 01/01/2000
TIMESTAMP_HIGH = 1491004800 # unix timestamp of 01/04/2017


class StressTester(object):

    def __init__(self, listen_count, user_count, batch_size):
        self.listen_count = listen_count
        self.user_count = user_count
        self.batch_size = batch_size

    def random_timestamp(self):
        """
        Returns a random timestamp between TIMESTAMP_LOW and TIMESTAMP_HIGH
        """
        return int(TIMESTAMP_LOW + (TIMESTAMP_HIGH - TIMESTAMP_LOW) * random.random())

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

    def random_listen(self, count=1):
        """
        Generates random listen data
        """

        typ = 'single'
        if count > 1:
            typ = 'import'

        listens= []
        for i in xrange(count):
            listens.append( 
                    {
                    'listened_at': self.random_timestamp(),
                    'track_metadata': {
                        'artist_name': self.random_string(),
                        'track_name': self.random_string(),
                        'release_name': self.random_string(),
                        'additional_info': {
                            'random_data': self.random_string(),
                        }
                    }
                })

        payload = {
            'listen_type': typ,
            'payload': listens
        }

        return payload

    def send_data(self, auth_token):
        send_url = '{}/1/submit-listens'.format(LB_URL)
        data = self.random_listen(self.batch_size)
        return requests.post(
            send_url,
            headers={'Authorization': 'Token {}'.format(auth_token)},
            data = json.dumps(data),
        )

    def user_submit(self, to_send, auth_token):
        accepted = 0
        rejected = 0
        percentage = 0
        rejections = {}
        for _ in xrange(to_send):
            response = self.send_data(auth_token)
            if response.status_code == 200:
                accepted += 1
            else:
                rejected += 1
                print(response.text)
                if response.status_code in rejections:
                    rejections[response.status_code] += 1
                else:
                    rejections[response.status_code] = 1
            if accepted >= to_send / 10:
                accepted = 0
                percentage += 10
                print("{} percent done for user with auth_token {}".format(percentage, auth_token))

        if rejected > 0:
            print(json.dumps(rejections, indent=4))

    def stress_test(self):
        tokens = []
        print("Creating users in the local server instance")
        for user in range(self.user_count):
            cur_token = str(uuid.uuid4())
            tokens.append(cur_token)
            self.send_data(cur_token)
        print("User creation done. Now sending listens through different threads.")

        for token in tokens:
            to_send = self.listen_count / self.user_count
            user_thread = threading.Thread(target=self.user_submit, args=(to_send, token))
            user_thread.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--listencount", dest="listen_count", type=int, help="specify the number of listens to send while testing")
    parser.add_argument("-u", "--usercount", dest="user_count", type=int, help="specify the number of users to spread the listens over")
    parser.add_argument("-b", "--batchsize", dest="batch_size", type=int, help="specify the number of listens per submission")
    args = parser.parse_args()
    if args.listen_count and args.user_count:
        st = StressTester(args.listen_count, args.user_count, args.batch_size)
        st.stress_test()
    else:
        print("Please provide all options required, see -h for help")
