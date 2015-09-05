#import logging.config
import os

# Certain modules (such as Pika) configure logging on a module-level context, so we have to
# configure logging as early as possible or Pika's loggers will be disabled by reconfiguring logging.
#logging.config.fileConfig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf'))

import listenstore

ListenStore = listenstore.ListenStore
