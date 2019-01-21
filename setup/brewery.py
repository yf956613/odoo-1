#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import argparse
import glob
import json
import logging
import os
import tempfile
import time
import shutil
import subprocess
import sys

exec(open(os.path.join(os.path.dirname(__file__), '..', 'odoo', 'release.py'), 'rb').read())
version = version.split('-')[0].replace('saas~', '')

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
DOCKERUSER = """
RUN groupadd -g %(group_id)s odoo \\
&& useradd -u %(user_id)s -g odoo -G audio,video odoo \\
&& mkdir /home/odoo \\
&& chown -R odoo:odoo /home/odoo \\
&& echo "odoo ALL= NOPASSWD: /usr/bin/pip" > /etc/sudoers.d/pip \\
&& echo "odoo ALL= NOPASSWD: /usr/bin/pip3" >> /etc/sudoers.d/pip
USER odoo
""" % {'group_id': os.getgid(), 'user_id': os.getuid()}


def run(cmd, cwd=None):
    logging.info('Running: %s', ' '.join(cmd))
    return subprocess.run(cmd, cwd=cwd)


class DockerOdoo():

    def __init__(self, src_file, image_name='odoo:packaging'):
        self.image_name = image_name
        self.docker_dir = tempfile.TemporaryDirectory(prefix='dockbuild_')
        docker_src_file = src_file
        self.docker_file = os.path.join(self.docker_dir.name, 'Dockerfile')
        shutil.copy(docker_src_file, self.docker_file)
        with open(self.docker_file, 'a+') as df:
            df.write(DOCKERUSER)
        self.volumes = []

    def build_image(self):
        run(['docker', 'build', '-t', self.image_name, '.'], cwd=self.docker_dir.name)

    def run(self, cmd, user=None):
        self.container_name = 'odoo_package_%s' % int(time.time())
        docker_cmd = [
            'docker', 'run', '--rm',
            '--name', self.container_name,
            '--init',
        ]
        for volume in self.volumes:
            docker_cmd.extend(['--volume=%s' % volume])
        if user:
            docker_cmd.extend(['-u', user])
        docker_cmd.extend([self.image_name, '/bin/bash', '-c', "%s" % cmd])
        run(docker_cmd)


def cleanup(args):
    if args.no_remove:
        logging.info('Buidl dir "%s" not removed', args.build_dir)
    else:
        logging.info('Removing build dir "%s"', args.build_dir)
        shutil.rmtree(args.build_dir)


def prepare_build_dir(args):
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
    run(cmd)
    addons_src = os.path.join(args.build_srcdir, 'addons/*')
    addons_dest = os.path.join(args.build_srcdir, 'odoo/addons/')
    logging.info('Moving addons from "%s" to "%s"', addons_src, addons_dest)
    for addon in glob.glob(addons_src):
        shutil.move(addon, addons_dest)


def src_build(args):
    pass


def py_build(args):
    logging.info("Building Python source package")

def deb_build(args):
    logging.info("Building Debian package")
    # create py xz package first
    odock = DockerOdoo(os.path.join(os.path.dirname(__file__), 'package.dfbuild'))
    odock.volumes.append('%s:/data/build' % args.build_dir)
    odock.run(
        'cd /data/build/odoo_src/ '
        '&& python3 setup.py sdist --quiet --formats=xztar --dist-dir=/data/build/'
    )
    odock.run(
        'cd /data/build/odoo_src '
        '&& dpkg-buildpackage -rfakeroot -uc -us'
    )

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
    prepare_build_dir(args)
    builders[args.build_type](args)
    cleanup(args)


def docker_build_image(args):
    """ Build docker image(s)"""
    logging.info("Building docker image...")
    odock = DockerOdoo(os.path.join(os.path.dirname(__file__), 'package.dfbuild'))
    odock.build_image()


if __name__ == '__main__':
    log_levels = {"debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARN, "error": logging.ERROR, "critical": logging.CRITICAL}
    main_parser = argparse.ArgumentParser(prog='Odoo brewery to build packages')
    main_parser.add_argument("--no-remove", action="store_true", help="don't remove build dir")
    subparsers = main_parser.add_subparsers()
    build_parser = subparsers.add_parser('build', help='Build Odoo package')
    build_parser.add_argument('build_type', choices=['deb', 'rpm', 'win', 'py', 'src'])
    build_parser.add_argument('--build-dir', '-d', help='Directory where the build will occur. Must be empty or non existing')
    build_parser.set_defaults(func=build)
    docker_parser = subparsers.add_parser('docker', help='Prepare docker image')
    docker_parser.set_defaults(func=docker_build_image)
    args = main_parser.parse_args()
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %I:%M:%S', level=log_levels['debug'])
    args.func(args)
