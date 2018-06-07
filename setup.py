import glob
import os
from setuptools import setup

version = os.environ.get('RELEASE_VERSION', '99.0.0.dev0')

setup(
    name='messybrainz',
    version=version,
    author='MessyBrainz',
    author_email='support@metabrainz.org',
    packages=['messybrainz'],
    scripts=[x for x in glob.glob('bin/*.py') if x != 'bin/__init__.py'],
    license='LICENSE.txt',
    description='python interface to the messybrainz database.',
    install_requires=[
        "SQLAlchemy == 1.2.5"
    ],
    zip_safe=False
)
