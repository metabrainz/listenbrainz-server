#!/usr/bin/env python
import time
import calendar
import listenstore

l = listenstore.ListenStore()

unixtime = int(calendar.timegm(time.gmtime()))
item = {'user_id':'rj','listened_at':unixtime,'body':{'foo':'bar','now':time.strftime("%c")}}
l.insert(item)

res = l.fetch_listens(uid='rj')

print list(res)
