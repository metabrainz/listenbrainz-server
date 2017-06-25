import os
from shutil import copyfile

if not os.path.exists("listenbrainz/config.py"):
    copyfile("listenbrainz/config.py.sample", "listenbrainz/config.py")
