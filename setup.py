import os
import re
from setuptools import find_packages, setup
try:  # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:  # for pip <= 9.0.3
    from pip.req import parse_requirements

from deepocli import __VERSION__

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# Read requirements
egg_reg_exp = re.compile('.*egg=(.*)-(.*)')
install_requires = []
dependency_links = []
for req in parse_requirements('requirements.txt', session='hack'):
    if req.link:
        dependency_links.append(req.link.url)
        match = egg_reg_exp.match(req.link.url)
        if match is None:
            raise Exception("When specifying a git dependency, please append '#egg={:egg-name}-{:egg-version}' to the url.")
        install_requires.append("{}=={}".format(match.group(1), match.group(2)))
    else:
        install_requires.append(str(req.req))

setup(
    name='deepocli',
    version=__VERSION__,
    scripts=['scripts/deepo'],
    packages=find_packages(),
    package_dir={
        'deepocli': 'deepocli',
    },
    include_package_data=True,
    package_data={
        '': ['*.ttf'],
    },
    description='Deepomatic CLI',
    long_description=README,
    author='deepomatic',
    author_email='support@deepomatic.com',
    install_requires=install_requires,
    dependency_links=dependency_links,
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
