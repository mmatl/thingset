"""Dataset for storing and retrieving Thingiverse objects.
"""
import argparse
import json
import logging
from lxml import html
import os
import requests
import time
import urllib
import urlparse

from visualization import Visualizer3D as vis

from .constants import LICENSE_IDS, CATEGORY_IDS
from .thing import Thing

class ThingiverseDataset(object):
    """A filesystem-based dataset of Thingiverse objects.
    """

    def __init__(self, path):
        """Initialize a Thingiverse dataset in a given directory.
        If the dataset exists, load it -- otherwise, initialize one.

        Parameters
        ----------
        path : str
            A directory for the dataset.
        """
        self._root = path
        self._thing_metadata = {
        }

        # If the Dataset hasn't been opened before, initialize it.
        if not os.path.exists(path):
            os.makedirs(path)
            return

        for name in os.listdir(self._root):
            thingpath = os.path.join(self._root, name)
            if os.path.isdir(thingpath):
                metadata = Thing.load_metadata(thingpath)
                if metadata:
                    thing_id = metadata['id']
                    self._thing_metadata[thing_id] = metadata

    @property
    def keys(self):
        """list of str : A list of the keys for Things in the dataset.
        """
        return self._thing_metadata.keys()

    @property
    def categories(self):
        """list of str : A list of categories available in the dataset.
        """
        return set([x['category'] for x in self._thing_metadata.itervalues()])

    def category_keys(self, category):
        """list of str : A list of keys for things in the given category.
        """
        keys = []
        for thing_id in self.keys:
            thing_category = self._thing_metadata[thing_id]['category']
            if thing_category == category:
                keys.append(thing_id)
        return keys

    def metadata(self, key):
        """Return metadata for a Thing in the database.
        """
        key = str(key)
        if key not in self._thing_metadata:
            raise KeyError(key)
        return self._thing_metadata[key]

    def search_by_metadata(self, key, value):
        """Return tuples of (thing_id, model_id) for all models that have a particular
        metadata key/value pair.
        """
        matches = {}
        for thing_id in self.keys:
            thing_metadata = self._thing_metadata[thing_id]
            model_ids = []
            for model_id in thing_metadata['models']:
                model_metadata = thing_metadata['models'][model_id]['metadata']
                if key in model_metadata and model_metadata[key] == value:
                    model_ids.append(model_id)
            if len(model_ids) > 0:
                matches[thing_id] = model_ids
        return matches

    def save(self, thing, only_metadata=False, model_keys=None):
        """Save a modified Thing out to the database.

        Parameters
        ----------
        thing : Thing
            The thing to save.
        only_metadata : bool
            If True, only the metadata is written (not the mesh filenames).
        model_keys : list of str
            The keys of the models to save. If None, all models are saved.
        """
        thingpath = os.path.join(self._root, thing.id)
        if not os.path.exists(thingpath):
            os.makedirs(thingpath)
        thing.export(thingpath, only_metadata, model_keys)
        self._thing_metadata[thing.id] = Thing.load_metadata(thingpath)

    def vis(self, key):
        """Show all the models for a given Thing.

        Parameters
        ----------
        key : str
            The key for the target Thing.
        """
        for model in self[key].models:
            vis.figure()
            vis.mesh(model.mesh, style='surface')
            vis.show()

    def retrieve_from_thingiverse(self, n, cache_dir, params=None):
        """Retrieve things from Thingiverse and save them to the dataset.

        Parameters
        ----------
        n : int
            The maximum number of things to save.
        cache_dir : str
            A cache directory for temporary mesh conversions
        params : dict
            A set of parameters, including 'category', 'license', and 'query'. Optional.
        """
        baseurl = 'http://www.thingiverse.com/search/page:{}?type=things'

        if params is None:
            baseurl = 'http://www.thingiverse.com/explore/newest/page:{}'
        else:
            if 'category' in params:
                if params['category'] not in CATEGORY_IDS:
                    raise ValueError('{} is an invalid category.'.format(params['category']))
                category_id = CATEGORY_IDS[params['category']]
                baseurl = '{}&category_id={}'.format(baseurl, category_id)

            if 'license' in params:
                if params['license'] not in LICENSE_IDS:
                    raise ValueError('{} is an invalid license.'.format(params['license']))
                license_id = LICENSE_IDS[params['license']]
                baseurl = '{}&license={}'.format(baseurl, license_id)

            if 'query' in params and params['query'] != '':
                baseurl = '{}&q={}'.format(baseurl, urllib.quote(params['query']))

        logging.log(31, 'Retrieving up to {} items from Thingiverse with parameters:'.format(n))
        logging.log(31, '\t{}'.format(json.dumps(params, indent=4)))

        # Iterate through available pages
        page = 1
        prev_path = ''
        num_imports = 0

        while True:
            # Load search page
            url = baseurl.format(page)
            page += 1

            # Prevent DDOS
            time.sleep(0.5)

            r = requests.get(url)

            logging.log(31, 'Retrieving page {}...'.format(page - 1))

            if r.status_code != 200:
                logging.log(32, 'Page {} retrieval failed.')
                logging.log(32, '\tQuery URL: {}'.format(url))
                logging.log(32, '\tStatus Code: {}'.format(r.status_code))
                continue

            # If prev url is same as new one, stop
            path = urlparse.urlparse(r.url).path
            if prev_path == path:
                return num_imports
            prev_path = path

            # Extract thing IDs
            root = html.fromstring(r.text)
            thing_ids = [x.get('data-id') for x in root.find_class('thing')]
            logging.log(31, '{} things retrieved on page {}.'.format(len(thing_ids), page - 1))
            if len(thing_ids) == 0:
                return num_imports

            # Retrieve and save things
            for thing_id in thing_ids:
                if thing_id in self.keys:
                    continue

                # Retrieve the thing
                t = Thing.retrieve(thing_id, cache_dir)
                if t is None:
                    continue

                # Export the thing, then lazy-load a copy to reduce memory usage.
                thingdir = os.path.join(self._root, t.id)
                if not os.path.exists(thingdir):
                    os.makedirs(thingdir)
                t.export(thingdir)
                self._thing_metadata[thing_id] = Thing.load_metadata(thingdir)

                num_imports += 1

                logging.log(31, '{}/{} things retrieved.'.format(num_imports, n))

                if num_imports >= n:
                    return num_imports

    def __getitem__(self, key):
        """Load a thing, including its objects.

        Parameters
        ----------
        key : str
            The key of the target thing.
        """
        key = str(key)
        if key not in self._thing_metadata:
            raise KeyError(key)
        thingpath = os.path.join(self._root, key)
        return Thing.load(thingpath)
