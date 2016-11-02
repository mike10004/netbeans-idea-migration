#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  transform_nbactions.py
#  
#  Copyright 2016 Mike <mchaberski@gmail.com>
#  
#  MIT License
#  

import logging
import xmljson
import xml.etree.ElementTree
import json
import collections
import jinja2
import os
import os.path
import fnmatch

_log = logging.getLogger('transform_nbactions')
_SANITARY_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'

def to_list(string_or_list):
    if string_or_list is None:
        return []
    if isinstance(string_or_list, basestring):
        return [string_or_list]
    else:
        assert isinstance(string_or_list, list) 
        return string_or_list

def sanitize(garbage):
    return ''.join([(c if c in _SANITARY_CHARS else '_') for c in garbage])

def to_defaultdict(src):
    d = collections.defaultdict(None)
    d.update(src)
    return d

def convert_action(action, args):
    action = to_defaultdict(action)
    if 'goals' not in action or len(action['goals']) == 0: 
        raise ValueError("action has no goals")
    if 'activatedProfiles' not in action:
        action['activatedProfiles'] = {
            'activatedProfile': []
        }
    name = args.name_prefix + action['displayName']
    properties = action.get('properties') or {}
    config = {
        'basename': sanitize(name),
        'name': name,
        'project': {
            'dirname': args.project_dir
        },
        'args': to_list(action.get('goals')['goal']),
        'properties': [{'name': k, 'value': properties[k]} for k in properties],
        'profiles': to_list(action['activatedProfiles']['activatedProfile'])
    }
    return config

def _mkdirs(path):
    if not os.path.isdir(path):
        if os.path.isfile(path): 
            raise ValueError("specified output directory is already a file: " + path)
        os.makedirs(path)
    return path

def main(args):
    logging.basicConfig(level=eval('logging.' + args.log_level))
    with open(args.nbactions_file, 'r') as ifile:
        xml_str = ifile.read()
    tree = xml.etree.ElementTree.fromstring(xml_str)
    nbactions = xmljson.parker.data(tree)
    actions = nbactions['action']
    jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(args.templates_dir), trim_blocks=True, lstrip_blocks=True)
    run_config_template = jenv.get_template('runConfigurationTemplate.xml')
    _log.debug("transforming actions matching pattern %s", args.action_filter)
    num_transformed = 0
    for action in actions:
        if fnmatch.fnmatch(action['displayName'], args.action_filter):
            _log.debug("converting action %s", action['displayName'])
            config = convert_action(action, args)
            output = run_config_template.render(config)
            if args.output_dir == '-':
                print output
            else:
                output_file = os.path.join(args.output_dir, config['basename'] + '.xml')
                _log.debug("writing rendered template of length %d to %s", len(output), output_file)
                _mkdirs(args.output_dir)
                with open(output_file, 'w') as ofile:
                    ofile.write(output)
            num_transformed += 1
        else:
            _log.debug("skipping action %s (pattern mismatch)", action['displayName'])
    _log.debug("transformed %d actions", num_transformed)
    if num_transformed == 0 and not args.allow_zero_actions:
        print >> sys.stderr, "transform_nbactions: no actions transformed; check filter pattern"
        return 1
    return 0

if __name__ == '__main__':
    import sys
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("--log-level", "-l", choices=('DEBUG', 'INFO', 'WARN', 'ERROR'), default='INFO', metavar="LEVEL", help="log level")
    p.add_argument("nbactions_file", help="pathname of the nbactions.xml file", metavar="FILE")
    p.add_argument("--name-prefix", help="prefix for configuration names", default='')
    p.add_argument("--project-dir", metavar="PATH", help="relative path of the project subdirectory")
    p.add_argument("--output-dir", metavar="DIRNAME", help="directory to write output files in; use - to dump to stdout", default=os.getcwd())
    p.add_argument("--templates-dir", metavar="DIRNAME", default=os.path.dirname(os.path.abspath(sys.argv[0])), help="directory containing the run configuration xml template")
    p.add_argument("--action-filter", metavar="PATTERN", help="wildcard pattern to restrict actions to be transformed; pattern must match action 'displayName'", default="*")
    p.add_argument("--allow-zero-actions", action="store_true", help="exit clean even if no actions are transformed")
    args = p.parse_args()
    sys.exit(main(args))
