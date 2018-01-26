#!/usr/bin/python
"""A script for adding things to a dataset.
"""
import argparse
import logging

from autolab_core import YamlConfig

from thingset import ThingiverseDataset

def main():
    # initialize logging
    logging.getLogger().setLevel(31)

    parser = argparse.ArgumentParser(
        description='Pull new data from Thingiverse',
        epilog='Written by Matthew Matl (mmatl)'
    )
    parser.add_argument('--config', help='config filename', default='cfg/tools/crawler.yaml')
    args = parser.parse_args()

    config_filename = args.config
    config = YamlConfig(config_filename)

    ds = ThingiverseDataset(config['dataset_dir'])
    for license in config['licenses']:
        for category in config['categories']:
            params = {
                'category' : category,
                'license' : license,
                'query' : ''
            }
            ds.retrieve_from_thingiverse(config['number'], config['cache_dir'], params)

if __name__ == "__main__":
    main()

