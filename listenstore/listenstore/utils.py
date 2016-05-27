import sys
import os.path
import argparse
from setproctitle import setproctitle
import json
import os
from loadconfig import Config

def get_config(opt_vars):
    """ Merge configuration from 'config.py' of ListenBrainz, commandline arguments and \
        the default values with order of preference

        Config_file > Commandline_arguments > Default_config
    """

    config = {}
    default_config = {  "KAFKA_CONNECT": "localhost:9092",
                        "CASSANDRA_SERVER": "localhost",
                        "CASSANDRA_KEYSPACE": "listenbrainz",
                        "CASSANDRA_REPLICATION_FACTOR": "1"
                     }
    try:
        custom_config = Config(os.path.dirname(__file__)).from_pyfile(opt_vars['CONFIG'])
    except:
        #TODO: Log failure loading config file
        pass

    config.update(default_config)
    config.update(opt_vars)
    config.update(custom_config)
    return config


def argparse_factory(desc):
    opt_parser = argparse.ArgumentParser(description=desc)
    opt_parser.add_argument('-c', '--config',
                            dest='CONFIG',
                            default=os.path.dirname(__file__) + "/../../config.py",
                            help='/path/to/config.py for configuration of listenstore')
    opt_parser.add_argument('-l', '--loglevel',
                            dest='LOGLEVEL',
                            default='INFO',
                            help='DEBUG | INFO | WARNING | ERROR | CRITICAL')
#    opt_parser.add_argument('-v',
#                            dest='VERBOSE',
#                            action='store_true',
#                            help='Enable logging to stdout',
#                            default=False)
    return opt_parser


def parse_args_and_config(opt_parser):
    conf = get_config(vars(opt_parser.parse_args()))
    set_process_title(conf)
    return conf


def get_process_name():
    return os.path.basename(sys.argv[0]).split('.')[0]


def set_process_title(config):
    setproctitle("%s" % (get_process_name()))
