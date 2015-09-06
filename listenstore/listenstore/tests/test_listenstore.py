# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import unittest
from datetime import date
from .. import listenstore


class RangeTestCase(unittest.TestCase):

    def testDateRange(self):
        self.assertEqual(listenstore.daterange(date(2015, 8, 12), 'day'), (2015, 8, 12))
        self.assertEqual(listenstore.daterange(date(2015, 8, 12), 'month'), (2015, 8))
        self.assertEqual(listenstore.daterange(date(2015, 8, 12), 'year'), (2015,))

    def testDateRanges(self):
        max_date = date(2015, 9, 6)
        min_date = date(2014, 6, 1)

        expected = [(2015, 9), (2015, 8), (2015, 7), (2015, 6), (2015, 5), (2015, 4),
                    (2015, 3), (2015, 2), (2015, 1), (2014, 12), (2014, 11), (2014, 10),
                    (2014, 9), (2014, 8), (2014, 7), (2014, 6)]

        self.assertEqual(list(listenstore.dateranges(listenstore.date_to_id(min_date),
                              listenstore.date_to_id(max_date), 'month')),
                         expected)
