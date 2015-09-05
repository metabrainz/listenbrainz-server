import glob
import os
from setuptools import setup

version = os.environ.get('RELEASE_VERSION', '99.0.0.dev0')

setup(
    name='listenbrainz-store',
    version=version,
    author='musicbrainz',
    author_email='foo@example.com',
    packages=['listenstore'],
    scripts=[x for x in glob.glob('bin/*.py') if x != 'bin/__init__.py'],
    package_data={'': ['logging.conf']},
    license='LICENSE.txt',
    description='python interface to listen data stored in cassandra',
    install_requires=[
        "cassandra-driver == 2.1.3",
        "setproctitle == 1.1.8"
    ],
    zip_safe=False
)
