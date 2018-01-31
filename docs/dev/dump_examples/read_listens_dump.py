import json
import os

def read_user_listens(username):
    with open('index.json') as f:
        index = json.load(f)

        # get the filename, offset and size for user
        # from the index
        file_name = index[username]['file_name']
        offset = index[username]['offset']
        size = index[username]['size']

        # directory structure of the form "listens/%s/%s/%s.listens" % (uuid[0], uuid[0:2], uuid)
        file_path = os.path.join('listens', file_name[0], file_name[0:2], '%s.listens' % file_name)
        with open(file_path) as listen_file:
            listen_file.seek(offset)
            listens = listen_file.read(size)
            return map(json.loads, listens.split('\n'))


if __name__ == '__main__':
    username = input('Enter the name of the user: ')
    for listen in read_user_listens(username):
        print(json.dumps(listen, indent=4))
