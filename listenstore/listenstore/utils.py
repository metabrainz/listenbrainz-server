import sys
import os.path
import argparse
from setproctitle import setproctitle
import json
import ConfigParser
import os

def config(opt_vars):
    """ Parse config file else return default values """
    config = ConfigParser.RawConfigParser()
    config.optionxform = str
    if len(config.read(os.path.dirname(__file__) + "/" + opt_vars['CONFIG'])) == 0:
        return {
            "KAFKA_SERVER": "localhost:9092",
            "CASSANDRA_SERVER": "localhost",
            "CASSANDRA_KEYSPACE": "listenbrainz"
        }

    values = []
    for sec in ['DEFAULT'] + config.sections():
        values +=  [ (key,val.strip("'").strip('"')) for key,val in config.items(sec) ]
    return dict(values)


def argparse_factory(desc):
    opt_parser = argparse.ArgumentParser(description=desc)
    opt_parser.add_argument('-c', '--config',
                            dest='CONFIG',
                            default='../listenstore.conf',
                            help='/path/to/listenstore.conf for configuration')
    opt_parser.add_argument('-l', '--loglevel',
                            dest='LOGLEVEL',
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
    conf = config(vars(opts))
    d = dict(dict(vars(opts)).items() + conf.items()) # Give preference to items in config file
    set_process_title(d)
    return d


def get_process_name():
    return os.path.basename(sys.argv[0]).split('.')[0]


def set_process_title(config):
    setproctitle("%s" % (get_process_name()))
