#!/usr/bin/python

import argparse
import datetime
import json
import logging
from lxml import html
import os
import requests
import time
import trimesh
import urllib
import urlparse

LICENSE_IDS = {
    "Creative Commons - Attribution" : "cc",
    "Creative Commons - Attribution - Share Alike" : "ccsa",
    "Creative Commons - Attribution - No Derivatives" : "ccnd",
    "Creative Commons - Attribution - Non-Commercial" : "ccnc",
    "Creative Commons - Attribution - Non-Commercial - Share Alike" : "ccncsa",
    "Creative Commons - Attribution - Non-Commercial - No Derivatives" : "ccncnd",
    "Creative Commons - Public Domain Dedication" : "pd0",
    "GNU - GPL" : "gpl",
    "GNU - LGPL" : "lgpl",
    "BSD License" : "bsd",
    "All Rights Reserved" : "none",
    "Nokia" : "nokia",
    "Public Domain" : "public",
}

CATEGORY_IDS = {
    "3d-printing" : "73",
    "art" : "63",
    "fashion" : "64",
    "gadgets" : "65",
    "hobby" : "66",
    "household" : "67",
    "learning" : "69",
    "models" : "70",
    "tools" : "71",
    "toys-and-games" : "72",
    "2d-art" : "144",
    "art-tools" : "75",
    "coins-and-badges" : "143",
    "interactive-art" : "78",
    "math-art" : "79",
    "scans-and-replicas" : "145",
    "sculptures" : "80",
    "signs-and-logos" : "76",
    "accessories" : "81",
    "bracelets" : "82",
    "costume" : "142",
    "earrings" : "139",
    "glasses" : "83",
    "jewelry" : "84",
    "keychains" : "130",
    "rings" : "85",
    "audio" : "141",
    "camera" : "86",
    "computer" : "87",
    "mobile-phone" : "88",
    "tablet" : "90",
    "videogames" : "91",
    "automotive" : "155",
    "diy" : "93",
    "electronics" : "92",
    "music" : "94",
    "rc-vehicles" : "95",
    "robotics" : "96",
    "sport-and-outdoors" : "140",
    "bathroom" : "147",
    "containers" : "146",
    "decor" : "97",
    "household-supplies" : "99",
    "kitchen-and-dining" : "100",
    "office" : "101",
    "organization" : "102",
    "outdoor-and-garden" : "98",
    "pets" : "103",
    "replacement-parts" : "153",
    "biology" : "106",
    "engineering" : "104",
    "math" : "105",
    "physics-and-astronomy" : "148",
    "animals" : "107",
    "buildings-and-structures" : "108",
    "creatures" : "109",
    "food-and-drink" : "110",
    "model-furniture" : "111",
    "model-robots" : "115",
    "people" : "112",
    "props" : "114",
    "vehicles" : "116",
    "hand-tools" : "118",
    "machine-tools" : "117",
    "parts" : "119",
    "tool-holders-and-boxes" : "120",
    "chess" : "151",
    "construction-toys" : "121",
    "dice" : "122",
    "games" : "123",
    "mechanical-toys" : "124",
    "playsets" : "113",
    "puzzles" : "125",
    "toy-and-game-accessories" : "149",
    "3d-printer-accessories" : "127",
    "3d-printer-extruders" : "152",
    "3d-printer-parts" : "128",
    "3d-printers" : "126",
    "3d-printing-tests" : "129"
}

class Thing(object):

    def __init__(self, thing_id, thing_name, author_name,
                 license_name, license_url, category,
                 access_time, models=None):

        self._id = thing_id
        self._name = thing_name
        self._link = 'https://www.thingiverse.com.thing:{}'.format(thing_id)
        self._author = author_name
        self._license = {
            'type' : license_name,
            'url'  : license_url
        }
        self._category = category
        self._access_time = access_time
        self._models = models

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def author(self):
        return self._author

    @property
    def license(self):
        return self._license

    @property
    def category(self):
        return self._category

    @property
    def access_time(self):
        return self._access_time

    @property
    def models(self):
        return self._models

    @property
    def meshes(self):
        return [m['mesh'] for m in self.models]

    def export(self, path):
        json_dict = {
            'id'            : self._id,
            'name'          : self._name,
            'link'          : self._link,
            'author'        : self._author,
            'license'       : self._license,
            'category'      : self._category,
            'access_time'   : self._access_time,
            'models' : []
        }

        # Export models
        for model in self._models:
            basename = '{}.obj'.format(model['id'])
            mesh_filename = os.path.join(path, basename)
            model['mesh'].export(mesh_filename)
            json_dict['models'].append({
                'id' : model['id'],
                'name' : model['name'],
                'mesh' : basename,
                'link' : 'https://www.thingiverse.com/download:{}'.format(model['id'])
            })

        # Export metadata
        json_filename = os.path.join(path, 'metadata.json')
        json.dump(json_dict, open(json_filename, 'w'), sort_keys=True, indent=4, separators=(',', ': '))

    @staticmethod
    def load_lazy(path):
        json_filename = os.path.join(path, 'metadata.json')
        try:
            json_dict = json.load(open(json_filename))
        except:
            return None

        return Thing(json_dict['id'], json_dict['name'], json_dict['author'],
                     json_dict['license']['type'], json_dict['license']['url'],
                     json_dict['category'], json_dict['access_time'])

    @staticmethod
    def load(path):
        json_filename = os.path.join(path, 'metadata.json')
        try:
            json_dict = json.load(open(json_filename))
        except:
            return None

        # Load mesh models
        models = []
        for model in json_dict['models']:
            mesh_filename = os.path.join(path, '{}.obj'.format(model['id']))
            mesh = trimesh.load_mesh(mesh_filename)
            models.append({
                'id' : model['id'],
                'name' : model['name'],
                'mesh' : mesh
            })

        return Thing(json_dict['id'], json_dict['name'], json_dict['author'],
                     json_dict['license']['type'], json_dict['license']['url'],
                     json_dict['category'], json_dict['access_time'], models)

    @staticmethod
    def retrieve(thing_id, cache_dir):

        # Make cache dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        # Retrieve a page for the thing
        url = 'https://www.thingiverse.com/thing:{}'.format(thing_id)

        logging.log(31, 'Retrieving thing {}...'.format(thing_id))

        r = requests.get(url)
        if r.status_code != 200:
            logging.log(32, 'Thing retrieval failed!')
            logging.log(32, '\tQuery URL: {}'.format(url))
            logging.log(32, '\tStatus Code: {}'.format(r.status_code))
            return None
        access_time = datetime.datetime.now().strftime("%I:%M%p on %d %B %Y")
        root = html.fromstring(r.text)

        # Retrieve basic metadata about the thing
        thing_name = root.find_class('thing-name')[0].text
        author_name = root.find_class('creator-name')[0][0].text
        license_name = root.find_class('thing-license')[0].get('title')
        license_url = root.find_rel_links('license')[0].get('href')
        _, category = os.path.split(root.find_class('thing-category')[0].get('href'))

        # Retrieve the individual cad files
        models = []
        links = root.find_class('thing-file-download-link')
        for a in links:
            # Retrieve metadata
            file_id = a.get('data-file-id')
            file_name = a.get('data-file-name')
            base_name, ext = os.path.splitext(file_name)
            if ext.lower() not in [".stl", ".obj", ".ply", ".off"]:
                continue

            # Download mesh
            link = 'https://www.thingiverse.com/download:{}'.format(file_id)
            logging.log(31, '\tRetrieving mesh {}!'.format(file_id))
            r = requests.get(link, stream=True)
            if r.status_code != 200:
                logging.log(32, '\tMesh retrieval failed!')
                logging.log(32, '\t\tQuery URL: {}'.format(link))
                logging.log(32, '\t\tStatus Code: {}'.format(r.status_code))
                continue

            output_filename = os.path.join(cache_dir, file_name)
            with open(output_filename, 'wb') as fout:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        fout.write(chunk)
            mesh = trimesh.load_mesh(output_filename)
            mesh.apply_scale(0.001)
            os.remove(output_filename)

            model_info = {
                'id' : file_id,
                'name' : base_name,
                'mesh' : mesh
            }

            models.append(model_info)


        return Thing(thing_id, thing_name, author_name,
                     license_name, license_url, category,
                     access_time, models)

class ThingiverseDataset(object):

    def __init__(self, path):
        self._root = path
        self._things = {
        }

        # If the Dataset hasn't been opened before, initialize it.
        if not os.path.exists(path):
            os.makedirs(path)
            return

        for name in os.listdir(self._root):
            thingpath = os.path.join(self._root, name)
            if os.path.isdir(thingpath):
                thing = Thing.load_lazy(thingpath)
                if thing:
                    self._things[thing.id] = thing

    @property
    def ids(self):
        return self._things.keys()

    @property
    def categories(self):
        return set([x.category for x in self._things.itervalues()])

    def category_ids(self, category):
        ids = []
        for thing_id in self.ids:
            thing = self[thing_id]
            if thing.category == category:
                ids.append(thing.id)
        return ids

    def retrieve_from_thingiverse(self, n, cache_dir, params=None):
        baseurl = 'http://www.thingiverse.com/search/page:{}?type=things'

        if params is None:
            baseurl = 'http://www.thingiverse.com/explore/newest/page:{}'
        else:
            if 'category' in params:
                if params['category'] not in CATEGORY_IDS:
                    raise ValueError('{} is an invalid category!'.format(params['category']))
                category_id = CATEGORY_IDS[params['category']]
                baseurl = '{}&category_id={}'.format(baseurl, category_id)

            if 'license' in params:
                if params['license'] not in LICENSE_IDS:
                    raise ValueError('{} is an invalid license!'.format(params['license']))
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
                logging.log(32, 'Page {} retrieval failed!')
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
                if thing_id in self.ids:
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
                self._things[thing_id] = Thing.load_lazy(thingdir)

                num_imports += 1

                logging.log(31, '{}/{} things retrieved!'.format(num_imports, n))

                if num_imports >= n:
                    return num_imports

    def __getitem__(self, key):
        key = str(key)
        thing = self._things[key]
        if thing.models is None:
            thingpath = os.path.join(self._root, thing.id)
            self._things[key] = Thing.load(thingpath)
            thing = self._things[key]
        return thing

def main():
    # initialize logging
    logging.getLogger().setLevel(31)

    parser = argparse.ArgumentParser(
            description="Crawl data from thingiverse",
            epilog="Written by Qingnan Zhou <qnzhou at gmail dot com> Modified by Mike Gleason")
    parser.add_argument("outdir", help="output directories")
    parser.add_argument("--cache-dir", "-c", help="cache directories",
            default=".")
    parser.add_argument("--number", "-n", type=int,
            help="how many files to crawl", default=1)
    args = parser.parse_args()

    output_dir = args.outdir
    cache_dir = args.cache_dir
    number = args.number

    params = {
        'category' : 'household',
        'license' : 'Creative Commons - Public Domain Dedication',
        'query' : ''
    }

    categories = [
        '3d-printing',
        'gadgets',
        'hobby',
        'household',
        'models',
        'tools',
        'toys-and-games',
        'art-tools',
        'scans-and-replicas',
        'sculptures',
        'audio',
        'computer',
        'sports-and-outdoors',
        'bathroom',
        'containers',
        'household-supplies',
        'kitchen-and-dining',
        'office',
        'organization',
        'outdoor-and-garden',
        'food-and-drink',
        'hand-tools',
        'machine-tools',
        'tool-holders-and-boxes'
    ]
    licenses = ['Creative Commons - Public Domain Dedication']

    ds = ThingiverseDataset(output_dir)
    for license in licenses:
        for category in categories:
            params = {
                'category' : category,
                'license' : license,
                'query' : ''
            }
            ds.retrieve_from_thingiverse(number, cache_dir, params)

if __name__ == "__main__":
    main()

