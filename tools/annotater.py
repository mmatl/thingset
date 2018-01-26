#!/usr/bin/python
"""A script for adding annotations to a dataset.
"""
import argparse
import logging

from autolab_core import YamlConfig
from visualization import Visualizer3D as vis

from thingset import ThingiverseDataset

def good_label_callback(viewer, model, key, value):
    model.metadata[key] = value
    viewer.on_close()

def main():
    # initialize logging
    logging.getLogger().setLevel(31)

    parser = argparse.ArgumentParser(
        description='Annotate Thingiverse Dataset Models',
        epilog='Written by Matthew Matl (mmatl)'
    )
    parser.add_argument('--config', help='config filename', default='cfg/tools/annotater.yaml')
    args = parser.parse_args()

    config_filename = args.config
    config = YamlConfig(config_filename)

    target_key = config['target_key']
    default_value = config['default_value']
    set_value = config['set_value']
    override = config['override']

    ds = ThingiverseDataset(config['dataset_dir'])
    for thing_id in ds.keys:
        thing = None
        thing_metadata = ds.metadata(thing_id)

        for model_id in thing_metadata['models']:
            model_data = thing_metadata['models'][model_id]
            if override or target_key not in model_data['metadata']:
                if thing is None:
                    thing = ds[thing_id]
                model = thing[model_id]
                logging.log(31, u"{} ({}): {} ({})".format(thing.name, thing.id, model.name, model.id).encode('utf-8'))
                model.metadata[target_key] = default_value
                vis.figure(registered_keys={'g' : (good_label_callback, [model, target_key, set_value])})
                vis.mesh(model.mesh, style='surface')
                vis.show(animate=True)

        if thing:
            ds.save(thing, only_metadata=True)

if __name__ == "__main__":
    main()
