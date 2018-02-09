#!/usr/bin/python
"""A script for fixing the dataset.
"""
import argparse
import logging
import re

from autolab_core import YamlConfig, SimilarityTransform
from visualization import Visualizer3D as vis

from thingset import ThingiverseDataset, Thing

def main():
    # initialize logging
    logging.getLogger().setLevel(31)

    parser = argparse.ArgumentParser(
        description='Annotate Thingiverse Dataset Models',
        epilog='Written by Matthew Matl (mmatl)'
    )
    parser.add_argument('--config', help='config filename', default='cfg/tools/fixer.yaml')
    args = parser.parse_args()

    config_filename = args.config
    config = YamlConfig(config_filename)

    ds = ThingiverseDataset(config['dataset_dir'])
    scale_key = config['scale_key']
    score_key = config['scale_key']
    cache_dir = config['cache_dir']

    thing_ids = [
        '562693',
        '2338550',
        '90830',
        '2587480',
        '2158012',
        '1484054',
        '1363175',
        '708889',
        '1906394'
    ]
    #for i, thing_id in enumerate(ds.keys):
    for i, thing_id in enumerate(thing_ids):
        logging.log(31, '{}/{} things...'.format(i, len(ds.keys)))
        # Load a thing
        thing = ds[thing_id]

        # Check each of its models for watertightness
        needs_redownload = False
        for model in thing.models:
            if not model.mesh.is_watertight:
                needs_redownload = True
                break

        if not needs_redownload:
            logging.log(31, 'Thing {} ok'.format(thing.id))
            continue

        logging.log(31, 'Redownloading thing {}'.format(thing.id))

        # Re-download the thing if needed
        new_thing = Thing.retrieve(thing.id, cache_dir)
        if new_thing is None:
            print "THING {} WAS NONE, SHOULD DELETE!!!".format(thing.id)
            continue

        # Create mapping from new model ids to old model ids
        mid_map = {}

        basename_to_cc_map = {}

        for model in new_thing.models:
            baseid = re.search('(.*)_cc_[0-9]*$', model.id)
            if baseid is None:
                if model.id in thing.model_keys:
                    mid_map[model.id] = model.id
            else:
                baseid = baseid.group(1)
                # Retrieve map from vertex counts to cc's
                if baseid not in basename_to_cc_map:
                    basename_to_cc_map[baseid] = {}
                    for old_model in thing.models:
                        if re.search('.*_cc_[0-9]*', old_model.id):
                            basename_to_cc_map[baseid][len(old_model.mesh.vertices)] = old_model.id

                # Find closest connected component to remap
                n_verts = len(model.mesh.vertices)
                if n_verts in basename_to_cc_map[baseid]:
                    mid_map[model.id] = basename_to_cc_map[baseid][n_verts]
                else:
                    print "HI"


        # For each model, update metadata and rescale if needed
        for model in new_thing.models:
            if not model.id in mid_map:
                model.metadata[score_key] = 0
            else:
                old_id = mid_map[model.id]
                old_metadata = thing[old_id].metadata
                model.metadata.update(old_metadata)
                if scale_key in old_metadata:
                    stf = SimilarityTransform(scale=old_metadata[scale_key])
                    model.mesh.apply_transform(stf.matrix)

        ds.save(new_thing)

if __name__ == "__main__":
    main()

