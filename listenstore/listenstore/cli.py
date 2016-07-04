from __future__ import division, absolute_import, print_function, unicode_literals
import os
import logging

from .utils import argparse_factory, parse_args_and_config
from .listenstore import PostgresListenStore


class Command(object):
    """ A simple class to make CLI tools and daemons easier to write.

        Override the run() method with the code you need to run.
    """
    desc = "(override this text to provide a description)"

    def __init__(self):
        """ Only override this method to add command line arguments.
            You have no logger, databases, or config in __init__. """
        self.opt_parser = argparse_factory(self.desc)
        self._listenStore = None


    # NB: only sets level after our Command starts running
    def set_log_level(self):
        l = self.config['LOGLEVEL']
        lev = logging.INFO
        if l == "DEBUG":
            lev = logging.DEBUG
        if l == "WARNING":
            lev = logging.WARNING
        if l == "ERROR":
            lev = logging.ERROR
        if l == "CRITICAL":
            lev = logging.CRITICAL
        self.log.setLevel(lev)


    def start(self):
        self.config = parse_args_and_config(self.opt_parser)
        self.log = logging.getLogger(__name__)
        self.set_log_level()
        try:
            self.run()
        except (KeyboardInterrupt, SystemExit):
            self.log.info("Exiting due to interrupt")
        except:
            self.log.exception("Exiting on exception")
            raise
        else:
           self.log.info("Exiting normally")
        finally:
           self.cleanup()


    def cleanup(self):
        return

    def run():
        """ Override this method with the body of your command. """
        raise NotImplementedError()

    @property
    def listen_store(self):
        """ Override this method in bin scripts to support writing
            to both Casandra and Postgres
        """
        pass

    def renice(self, increment):
        os.nice(increment)
