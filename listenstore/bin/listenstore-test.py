#!/usr/bin/env python
from listenstore.cli import Command


class ListenPrinter(Command):
    desc = "Print listens fetched from cassandra"

    def run(self):
        self.log.info("ListenPrinter starting..")
        #unixtime = int(calendar.timegm(time.gmtime()))
        #item = {'user_id':'rj','listened_at':unixtime,'body':{'foo':'bar','now':time.strftime("%c")}}
        #self.listen_store.insert(item)

        res = self.listen_store.fetch_listens(uid='rj')
        for r in res:
            print repr(r)

if __name__ == '__main__':
    ListenPrinter().start()
