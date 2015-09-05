#!/usr/bin/env python
import time
import calendar
import listendb.ListenStore

l = ListenStore()

unixtime = int(calendar.timegm(time.gmtime()))
item = {'user_id':'rj','listened_at':unixtime,'body':{'foo':'bar','now':time.strftime("%c")}}
l.insert(item)

res = l.fetch_listens(uid='rj')

print list(res)
