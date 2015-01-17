import os
from setuptools import setup, find_packages

os.chdir(os.path.dirname(os.path.realpath(__file__)))


def get_requirements():
    """
    To update the requirements for Evennia, edit the requirements.txt file.
    """
    req_lines = open('requirements.txt', 'r').readlines()
    reqs = []
    for line in req_lines:
        # Avoid adding comments.
        line = line.split('#')[0].strip()
        if line:
            reqs.append(line)
    return reqs

VERSION_PATH = os.path.join('evennia', 'VERSION.txt')


def get_version():
    """
    When updating the Evennia package for release, remember to increment the
    version number in evennia/VERSION.txt
    """
    return open(VERSION_PATH).read().strip()


def package_data():
    """
    By default, the distribution tools ignore all non-python files.

    Make sure we get everything.
    """
    file_set = []
    for root, dirs, files in os.walk('evennia'):
        for f in files:
            if '.git' in f.split(os.path.normpath(os.path.join(root, f))):
                # Prevent the repo from bing added.
                continue
            file_name = os.path.relpath(os.path.join(root, f), 'evennia')
            file_set.append(file_name)
    return file_set

setup(
    name='evennia',
    version=get_version(),
    description='A full-featured MUD building toolkit.',
    packages=find_packages(),
    scripts=['bin/evennia', 'bin/evennia_runner.py'],
    install_requires=get_requirements(),
    package_data={'': package_data()},
    zip_safe=False
)
