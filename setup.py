"""
Setup of core python codebase
Author: Jeff Mahler
"""
from setuptools import setup

requirements = [
    'autolab_core',
    'numpy',
    'lxml',
    'pyyaml',
    'trimesh',
    'visualization',
]

exec(open('thingset/version.py').read())


setup(
    name='thingset',
    version = __version__,
    description = 'Thingiverse dataset downloader and parser',
    long_description = 'Thingiverse dataset downloader and parser',
    author = 'Matthew Matl',
    author_email = 'matthewcmatl@gmail.com',
    license = 'MIT Software License',
    url = 'https://github.com/mmatl/thingset',
    keywords = '3D modeling printing dataset',
    classifiers = [
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Natural Language :: English',
        'Topic :: Scientific/Engineering'
    ],
    packages = ['thingset'],
    install_requires = requirements,
)

