# coding: utf-8
"""
Small tool to convert simple yaml demo data files.
SHOULD NOT STAY IN ODOO DIR
"""
from __future__ import print_function
from odoo.tools import yaml_tag
from odoo.tools.yaml_import import is_record, is_string
from lxml import etree
import yaml
import argparse
import sys
import os

def yaml_read(file_path):
    print("Reading file: {}".format(file_path), file=sys.stderr)
    with open(file_path, 'r') as yf:
        ydata = yf.read()
    return yaml.load(ydata)

def record_add_field(xml_record, yaml_field, yaml_value):
    f = etree.SubElement(xml_record, "field", name=yaml_field)
    if yaml_field.endswith('_id') or not isinstance(yaml_value, str):
        f.set('eval', str(yaml_value))
    else:
        f.text = yaml_value

def to_xml(yaml_nodes):
    root = etree.Element("data", noupdate="0")
    for node in yaml_nodes:
        if is_record(node):
            yaml_record = node.keys()[0]
            rec = etree.SubElement(root, "record")
            rec.set('id', yaml_record.id)
            rec.set('model', yaml_record.model)
            for yaml_field,yaml_value in node[yaml_record].items():
                record_add_field(rec, yaml_field, yaml_value)            
        elif is_string(node):
            root.append(etree.Comment(node))
        else:
            print("This node is not a record: {}".format(node), file=sys.stderr)
    print(etree.tostring(root, pretty_print=True))

if __name__ == '__main__':

    ap = argparse.ArgumentParser()
    ap.add_argument('start_path', type=str, help="Starting directory for searching yml files or a file.")
    ap.add_argument('--path_keyword', type=str, default="demo")
    
    options = ap.parse_args()
    if not os.path.isdir(options.start_path) and not os.path.isfile(options.start_path):
        print("Starting path must be a path or a file", file=sys.stderr)
        sys.exit(1)

    yaml_tag.add_constructors()

    if os.path.isdir(options.start_path):
        for base_path, dirs, files in os.walk(options.start_path):
            for f in files:
                fp = os.path.join(base_path, f)
                if f.endswith('yml') and options.path_keyword in fp:
                    to_xml(yaml_read(fp))
    else:
        to_xml(yaml_read(options.start_path))
   
