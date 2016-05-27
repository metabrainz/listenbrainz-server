import os
import types
from werkzeug.utils import import_string
string_types = (str,)

class Config(dict):
    def __init__(self, root_path):
        self.root_path = root_path
        self.configuration = {}

    def from_pyfile(self, filename, silent=False):
        filename = os.path.join(self.root_path, filename)
        d = types.ModuleType('listenstore.conf')
        d.__file__ = filename
        try:
            with open(filename) as config_file:
                exec(compile(config_file.read(), filename, 'exec'), d.__dict__)
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        self.from_object(d)
        return self.configuration

    def from_object(self, obj):
        if isinstance(obj, string_types):
            obj = import_string(obj)
        for key in dir(obj):
            if key.isupper():
                self.configuration[key] = getattr(obj, key)
