#!/usr/bin/python
"""A script for rescaling meshes in a dataset.
"""
import argparse
import logging
import numpy as np
import trimesh

from autolab_core import YamlConfig, RigidTransform, SimilarityTransform
from visualization import Visualizer3D as vis

from thingset import ThingiverseDataset

def rescale_callback(viewer, key, rot, stf, adder):
    if stf.scale + adder <= 0:
        return
    stf.scale += adder
    vis.get_object(key).T_obj_world = rot.dot(stf)

def rotate_callback(viewer, key, rot, stf):
    rot.rotation = RigidTransform.z_axis_rotation(np.pi / 2.0).dot(rot.rotation)
    vis.get_object(key).T_obj_world = rot.dot(stf)

def main():
    # initialize logging
    logging.getLogger().setLevel(31)

    # parse args
    parser = argparse.ArgumentParser(
        description='Annotate Thingiverse Dataset Models',
        epilog='Written by Matthew Matl (mmatl)'
    )
    parser.add_argument('--config', help='config filename', default='cfg/tools/rescaler.yaml')
    args = parser.parse_args()

    # read config
    config_filename = args.config
    config = YamlConfig(config_filename)

    # get gripper mesh
    gripper_filename = config['gripper_filename']
    gripper_mesh = trimesh.load_mesh(gripper_filename)

    # get metadata information
    identifier_key = config['identifier_key']
    identifier_value = config['identifier_value']
    scale_key = config['scale_key']
    default_scale = config['default_scale']
    override = config['override']

    ds = ThingiverseDataset(config['dataset_dir'])

    for i, thing_id in enumerate(ds.keys):
        thing = None
        thing_metadata = ds.metadata(thing_id)

        changed_model_keys = []

        for model_id in thing_metadata['models']:
            model_data = thing_metadata['models'][model_id]

            # If the identifier isn't in the model's metadata, skip it
            if identifier_key not in model_data['metadata'] or model_data['metadata'][identifier_key] != identifier_value:
                continue

            # If we're overriding or the scale key hasn't been set, modify the model
            if override or scale_key not in model_data['metadata']:

                # Load the model
                if thing is None:
                    thing = ds[thing_id]
                model = thing[model_id]
                logging.log(31, u"{} ({}): {} ({})".format(thing.name, thing.id, model.name, model.id).encode('utf-8'))
                changed_model_keys.append(model.id)

                # Rescale back to original dimensions if overriding
                if scale_key in model.metadata:
                    model.mesh.apply_scale(1.0 / model.metadata[scale_key])

                model.metadata[scale_key] = default_scale

                # Visualize the model, registering the grow/shrink callbacks
                stf = SimilarityTransform(from_frame='world', to_frame='world')
                rot = RigidTransform(from_frame='world', to_frame='world')

                registered_keys= {
                    'j' : (rescale_callback, ['model', rot, stf, 0.1]),
                    'k' : (rescale_callback, ['model', rot, stf, -0.1]),
                    'u' : (rescale_callback, ['model', rot, stf, 1.0]),
                    'i' : (rescale_callback, ['model', rot, stf, -1.0]),
                    'h' : (rotate_callback,  ['model', rot, stf])
                }
                vis.figure()
                vis.mesh(gripper_mesh, T_mesh_world=RigidTransform(translation=(0,0,-0.08), from_frame='obj', to_frame='world'), style='surface', color=(0.3, 0.3, 0.3), name='gripper')
                vis.mesh(model.mesh, style='surface', name='model')
                vis.show(animate=True, registered_keys=registered_keys)
                # Transform the model and update its metadata
                model.mesh.apply_transform(stf.matrix)
                model.metadata[scale_key] = stf.scale

        if thing:
            ds.save(thing, only_metadata=False, model_keys=changed_model_keys)
        logging.log(31, '{}/{} things...'.format(i, len(ds.keys)))

if __name__ == "__main__":
    main()

