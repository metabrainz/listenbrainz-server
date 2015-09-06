import sys
import os.path
import argparse
from setproctitle import setproctitle
import json


## TODO read config from whereever
def config():
    return {
        "kafka_server": "localhost:9092",
        "cassandra_server": "localhost",
        "cassandra_keyspace": "listenbrainz"
    }


def argparse_factory(desc):
    opt_parser = argparse.ArgumentParser(description=desc)
    # TODO not using any config file yet
    opt_parser.add_argument('-c', '--config',
                            dest='config',
                            default='./listenstore.conf',
                            help='/path/to/listenstore.conf for configuration')
    opt_parser.add_argument('-l', '--loglevel',
                            dest='loglevel',
                            default='INFO',
                            help='DEBUG | INFO | WARNING | ERROR | CRITICAL')
#    opt_parser.add_argument('-v',
#                            dest='verbose',
#                            action='store_true',
#                            help='Enable logging to stdout',
#                            default=False)
    return opt_parser


def parse_args_and_config(opt_parser):
    opts = opt_parser.parse_args()
    conf = config()
    d = dict(conf.items() + dict(vars(opts)).items())
    set_process_title(d)
    return d


def get_process_name():
    return os.path.basename(sys.argv[0]).split('.')[0]


def set_process_title(config):
    setproctitle("%s" % (get_process_name()))
