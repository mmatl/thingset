#!/usr/bin/python
"""A script for extracting the labelled meshes from a dataset
"""
import argparse
import logging
import numpy as np
import trimesh

from autolab_core import YamlConfig, RigidTransform, SimilarityTransform
from visualization import Visualizer3D as vis

from thingset import ThingiverseDataset

def main():
    # initialize logging
    logging.getLogger().setLevel(31)

    # parse args
    parser = argparse.ArgumentParser(
        description='Extract labelled models from a Thingiverse Dataset',
        epilog='Written by Matthew Matl (mmatl)'
    )
    parser.add_argument('--config', help='config filename', default='cfg/tools/extractor.yaml')
    args = parser.parse_args()

    # read config
    config_filename = args.config
    config = YamlConfig(config_filename)

    # get metadata information
    identifier_key = config['identifier_key']
    identifier_value = config['identifier_value']

    dsold = ThingiverseDataset(config['dataset_dir'])
    dsnew = ThingiverseDataset(config['output_dir'])

    for i, thing_id in enumerate(dsold.keys):
        thing_metadata = dsold.metadata(thing_id)

        model_keys = []

        for model_id in thing_metadata['models']:
            model_data = thing_metadata['models'][model_id]

            # If the identifier isn't in the model's metadata, skip it
            if identifier_key in model_data['metadata'] and model_data['metadata'][identifier_key] == identifier_value:
                model_keys.append(model_id)

        if len(model_keys) > 0:
            thing = dsold[thing_id]
            dsnew.save(thing.copy(model_keys))

if __name__ == "__main__":
    main()


