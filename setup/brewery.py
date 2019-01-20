#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import argparse
import logging
import os
import tempfile
import shutil
import subprocess
import sys

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

def run(cmd, cwd=None):
    logging.info('Running: %s', ' '.join(cmd))
    return subprocess.run(cmd, cwd=args.build_dir)

def cleanup(args):
    if not args.no_remove:
        logging.info('Removing build dir "%s"', args.build_dir)
        shutil.rmtree(args.build_dir)

def _prepare_build_dir(args):
    if args.build_dir:
        args.build_dir = os.path.abspath(args.build_dir)
        if not os.path.exists(args.build_dir):
            os.makedirs(args.build_dir)
        else:
            if os.listdir(args.build_dir):
                logging.error('Build dir not empty')
                sys.exit(1)
    else:
        args.build_dir = tempfile.mkdtemp(prefix='odoo_build')
    logging.info('Build dir: %s', args.build_dir)
    args.build_srcdir = os.path.join(args.build_dir, 'odoo_src')
    cmd = ['rsync', '-a', '--exclude', '.git', '--exclude', '*.pyc', '--exclude', '*.pyo']
    if args.build_type != 'win':
        cmd += ['--exclude', 'setup/win32']
    cmd += ['%s/' % SRC_DIR, args.build_srcdir]
    logging.info('Copying Odoo files to %s', args.build_srcdir)
    ret = run(cmd)

def src_build(args):
    pass

def py_build(args):
    pass

def deb_build(args):
    print("Debuild")

def rpm_build(args):
    pass

def win_build(args):
    pass

def build(args):
    builders = {
        'src': src_build,
        'py': py_build,
        'deb': deb_build,
        'rpm': rpm_build,
        'win': win_build,
    }
    _prepare_build_dir(args)
    builders[args.build_type](args)

def docker_command(args):
    pass

if __name__ == '__main__':
    log_levels = { "debug" : logging.DEBUG, "info": logging.INFO, "warning": logging.WARN, "error": logging.ERROR, "critical": logging.CRITICAL }
    main_parser = argparse.ArgumentParser(prog='Odoo brewery to build packages')
    main_parser.add_argument("--no-remove", action="store_true", help="don't remove build dir")
    subparsers = main_parser.add_subparsers()
    build_parser = subparsers.add_parser('build', help='Build Odoo package')
    build_parser.add_argument('build_type', choices=['deb', 'rpm', 'win', 'py', 'src'])
    build_parser.add_argument('--build-dir', '-d', help='Directory where the build will occur. Must be empty or non existing')
    build_parser.set_defaults(func=build)
    docker_parser = subparsers.add_parser('docker', help='Prepare docker images')
    docker_parser.set_defaults(func=docker_command)
    args = main_parser.parse_args()
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %I:%M:%S', level=log_levels['debug'])
    args.func(args)
    cleanup(args)
