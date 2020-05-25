# coding=utf-8

import calendar
import logging
import time

from listenbrainz.listenstore import ORDER_ASC, ORDER_DESC, DEFAULT_LISTENS_PER_FETCH


class ListenStore(object):
    MAX_FETCH = 5000          # max batch size to fetch from the db
    MAX_FUTURE_SECONDS = 600  # 10 mins in future - max fwd clock skew


    def __init__(self, logger):
        self.log = logger

    def max_id(self):
        return int(self.MAX_FUTURE_SECONDS + calendar.timegm(time.gmtime()))


    def fetch_listens_from_storage(self):
        """ Override this method in PostgresListenStore class """
        raise NotImplementedError()


    def get_total_listen_count(self):
        """ Return the total number of listens stored in the ListenStore """
        raise NotImplementedError()


    def get_listen_count_for_user(self, user_name, need_exact):
        """ Override this method in ListenStore implementation class

        Args:
            user_name: the user to get listens for
            need_exact: if True, get an exact number of listens directly from the ListenStore
                        otherwise, can get from a cache also
        """
        raise NotImplementedError()


    def dump_listens(self, location, dump_time, threads=None):
        """ Override this method in the implementation class.

        Args:
            location (str): the directory where the listens dump archive should be created
            dump_time (datetime): the time at which the data dump was started
            threads (int): the number of threads to user for compression

        Returns:
            the path to the dump archive
        """
        raise NotImplementedError()


    def import_listens_dump(self, archive_path, threads=None):
        """ Override this method in the implementation class.

        Args:
            archive (str): the path to the listens dump .tar.xz archive to be imported
            threads (int): the number of threads to be used for decompression (defaults to 1)
        """
        raise NotImplementedError()


    def fetch_listens(self, user_name, from_ts=None, to_ts=None, limit=DEFAULT_LISTENS_PER_FETCH, try_harder=0):
        """ Check from_ts, to_ts, and limit for fetching listens
            and set them to default values if not given.
        """
        if from_ts and to_ts:
            raise ValueError("You cannot specify from_ts and to_ts at the same time.")

        if from_ts is None and to_ts is None:
            raise ValueError("You must specify either from_ts or to_ts.")

        if from_ts:
            order = ORDER_ASC
        else:
            order = ORDER_DESC

        return self.fetch_listens_from_storage(user_name, from_ts, to_ts, limit, order, try_harder)
