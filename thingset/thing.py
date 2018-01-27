"""Model and Thing from Thingiverse Dataset
"""
import datetime
import json
import logging
from lxml import html
import os
import re
import requests
import trimesh

from .constants import MAX_N_FACES

class Model(object):
    """A single model from a Thingiverse Thing.
    """

    def __init__(self, model_id, model_name, mesh, metadata=None):
        """Create a Thingiverse model.

        Parameters
        ----------
        model_id : str
            The id key for the model.
        model_name : str
            A human-readable name for the model.
        mesh : trimesh.Trimesh
            The geometry of the model.
        metadata : dict
            Annotated metadata for the model.
        """
        self._model_id = model_id
        self._model_name = model_name
        self._mesh = mesh
        if metadata is None:
            metadata = {}
        self._metadata = metadata

    @property
    def id(self):
        """str : The id key for the model.
        """
        return self._model_id

    @property
    def name(self):
        """str : A human-readable name for the model.
        """
        return self._model_name

    @property
    def mesh(self):
        """trimesh.Trimesh : The geometry of the model.
        """
        return self._mesh

    @property
    def metadata(self):
        """dict : Annotated metadata for the model.
        """
        return self._metadata


class Thing(object):
    """A Thingiverse Thing, which is a collection of models and associated metadata.
    """

    def __init__(self, thing_id, thing_name, author_name,
                 license_name, license_url, category,
                 access_time, models=None):
        """Create a thing.

        Parameters
        ----------
        thing_id : str
            The id key for the thing.
        thing_name : str
            A human-readable name for the thing.
        author_name : str
            The username of the Thingiverse author who created the thing.
        license_name : str
            The string identifier for the license type.
        license_url : str
            A URL linking to the license in question.
        access_time : str
            A human-readable time at which the thing was downloaded.
        models : dict
            A map from model ids to Model objects.
        """
        self._id = thing_id
        self._name = thing_name
        self._link = 'https://www.thingiverse/com.thing:{}'.format(thing_id)
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
        return self._models.values()

    @property
    def meshes(self):
        return [m.mesh for m in self.models]

    def export(self, path, only_metadata=False, model_keys=None):
        """Save the thing to the given directory.

        Parameters
        ----------
        path : str
            A directory in which to save the thing.
        only_metadata : bool
            If True, only the metadata is written (not the mesh filenames).
        model_keys : list of str
            The keys of the models to save. If None, all models are saved.
        """
        json_dict = {
            'id'            : self._id,
            'name'          : self._name,
            'link'          : self._link,
            'author'        : self._author,
            'license'       : self._license,
            'category'      : self._category,
            'access_time'   : self._access_time,
            'models'        : {}
        }
        if model_keys is None:
            model_keys = [m.id for m in self.models]

        # Export models
        for model in self.models:
            basename = '{}.obj'.format(model.id)
            mesh_filename = os.path.join(path, basename)
            if not only_metadata and model.id in model_keys:
                model.mesh.export(mesh_filename)
            baseid = re.search('(.*)_cc_[0-9]*$', model.id)
            if baseid is None:
                baseid = model.id
            else:
                baseid = baseid.group(1)
            json_dict['models'][model.id] = {
                'name' : model.name,
                'mesh' : basename,
                'metadata' : model.metadata,
                'link' : 'https://www.thingiverse.com/download:{}'.format(baseid)
            }

        # Export metadata
        json_filename = os.path.join(path, 'metadata.json')
        json.dump(json_dict, open(json_filename, 'w'), sort_keys=True, indent=4, separators=(',', ': '))

    def __getitem__(self, key):
        """Retrieve a particular model.

        Parameters
        ----------
        key : str
            The key of the target model.
        """
        key = str(key)
        if key not in self._models:
            raise KeyError(key)
        return self._models[key]

    @staticmethod
    def load_metadata(path):
        """Load thing metadata file from a path.

        Parameters
        ----------
        path : str
            A directory in which the thing was saved.

        Returns
        -------
        dict
            The thing's metadata.
        """
        json_filename = os.path.join(path, 'metadata.json')
        try:
            json_dict = json.load(open(json_filename))
        except:
            return None
        return json_dict

    @staticmethod
    def load(path):
        """Load a thing, including its models.

        Parameters
        ----------
        path : str
            A directory in which the thing was saved.

        Returns
        -------
        Thing
            The thing stored in the given directory.
        """
        json_dict = Thing.load_metadata(path)
        if json_dict is None:
            return None

        # Load mesh models
        models = {}
        for model_id in json_dict['models']:
            model = json_dict['models'][model_id]
            mesh_filename = os.path.join(path, '{}.obj'.format(model_id))
            mesh = trimesh.load_mesh(mesh_filename)
            models[model_id] = Model(model_id, model['name'], mesh, model['metadata'])

        return Thing(json_dict['id'], json_dict['name'], json_dict['author'],
                     json_dict['license']['type'], json_dict['license']['url'],
                     json_dict['category'], json_dict['access_time'], models)

    @staticmethod
    def retrieve(thing_id, cache_dir, max_faces=MAX_N_FACES):
        """Load a thing from Thingiverse.

        Parameters
        ----------
        thing_id : str
            An ID for the thing.
        cache_dir : str
            Path to a cache directory for temporary 3D model conversion.
        max_faces : int
            A threshold on the number of faces allowed in a single model (doesn't save
            any models larger than this).

        Returns
        -------
        Thing
            The thing downloaded from Thingiverse, or None if no such thing exists or if
            none of the Thing's models were valid.
        """

        # Make cache dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        # Retrieve a page for the thing
        url = 'https://www.thingiverse.com/thing:{}'.format(thing_id)

        logging.log(31, 'Retrieving thing {}...'.format(thing_id))

        r = requests.get(url)
        if r.status_code != 200:
            logging.log(32, 'Thing retrieval failed.')
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
        models = {}
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
            logging.log(31, '\tRetrieving mesh {}.'.format(file_id))
            r = requests.get(link, stream=True)
            if r.status_code != 200:
                logging.log(32, '\tMesh retrieval failed.')
                logging.log(32, '\t\tQuery URL: {}'.format(link))
                logging.log(32, '\t\tStatus Code: {}'.format(r.status_code))
                continue

            output_filename = os.path.join(cache_dir, file_name)
            with open(output_filename, 'wb') as fout:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        fout.write(chunk)

            try:
                mesh = trimesh.load_mesh(output_filename)
                mesh.apply_scale(0.001)
            except:
                logging.log(32, '\t\tUnable to load mesh file.')
                os.remove(output_filename)
                continue

            os.remove(output_filename)

            if mesh.faces.shape[0] > max_faces:
                logging.log(32, '\t\tMesh had {} faces, more than allowable.'.format(mesh.faces.shape[0]))
                continue

            if not mesh.is_watertight:
                logging.log(32, '\t\tMesh was not watertight, skipping.')
                continue

            ccs = None

            try:
                # Patch up the normals, if necessary
                mesh.fix_normals()
                # Split the mesh by connected components
                ccs = mesh.split()
            except:
                logging.log(32, '\t\tUnable to process mesh file.')
                continue

            # If only one CC, re-center it and save it
            if len(ccs) == 1:
                mesh.apply_translation(-mesh.center_mass)
                models[file_id] = Model(file_id, base_name, mesh)

            # Otherwise, save each of the connected components separately
            else:
                logging.log(31, '\t\tMesh had {} connected components, splitting.'.format(len(ccs)))
                for i, cc in enumerate(ccs):
                    cc.apply_translation(-cc.center_mass)
                    file_id_str = '{}_cc_{}'.format(file_id, i)
                    models[file_id_str] = Model(file_id_str, '{}_cc_{}'.format(base_name, i), cc)

        if len(models) > 0:
            return Thing(thing_id, thing_name, author_name,
                        license_name, license_url, category,
                        access_time, models)
        else:
            return None


