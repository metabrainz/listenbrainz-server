#!/usr/bin/env python
from listenstore.cli import Command


class ListenTool(Command):
    desc = "Print listens fetched from cassandra"

    def __init__(self):
        super(ListenTool, self).__init__()
        self.opt_parser.add_argument('-u', dest='userid', required=True, help="User ID")
        self.opt_parser.add_argument('-n', dest='limit', type=int, default=10, help="Number of rows to fetch")

    def run(self):
        uid = self.config['userid']
        self.log.info("ListenTool starting for uid %s.." % (uid))
        res = self.listen_store.fetch_listens(uid=uid, limit=self.config['limit'])
        for r in res:
            print repr(r)

if __name__ == '__main__':
    ListenTool().start()
