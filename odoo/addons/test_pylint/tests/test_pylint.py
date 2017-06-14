# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
try:
    import pylint
except ImportError:
    pylint = None
import subprocess
from distutils.version import LooseVersion
import os

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestPyLint(TransactionCase):

    def _skip_test(self, reason):
        _logger.warn(reason)
        self.skipTest(reason)

    def test_pylint(self):
        if pylint is None:
            self._skip_test('please install pylint')
        if LooseVersion(getattr(pylint, '__version__', '0.0.1')) < LooseVersion('1.6.4'):
            self._skip_test('please upgrade pylint to >= 1.6.4')

        process = subprocess.Popen(['./pylint-test-bin.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.path.dirname(os.path.realpath(__file__)))
        out, err = process.communicate()
        if process.returncode:
            self.fail("\n" + out + "\n" + err)
