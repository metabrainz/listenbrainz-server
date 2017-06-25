import os
from shutil import copyfile

# IMPORTANT NOTE: This file exists only for use with building docs!

if not os.path.exists("listenbrainz/config.py"):
    copyfile("listenbrainz/config.py.sample", "listenbrainz/config.py")
