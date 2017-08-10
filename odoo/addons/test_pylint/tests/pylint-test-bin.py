#!/usr/bin/env python
import os
import sys

from pylint import lint
from pylint.lint import MANAGER
from pylint.reporters import BaseReporter

odoo_path = os.path.dirname(os.path.realpath(__file__ + '../../../../../'))
sys.path.append(odoo_path)
from odoo import tools
from odoo.modules import get_modules, get_module_path
from odoo.tools.lru import LRU


class lrucache(LRU):
    def setdefault(self, key, value):
        if key in self:
            return self[key]
        self[key] = value
        return value


class Reporter(BaseReporter):
    def __init__(self, output=None):
        super(Reporter, self).__init__(output)
        self.messages = []

    def handle_message(self, message):
        self.messages.append({
            'id': message.msg_id,
            'path': message.path,
            'line': message.line,
            'message': message.msg,
        })


ENABLED_CODES = [
    'E0601',  # using variable before assignment
    'W0123',  # eval used
    'W0101',  # unreachable code

    'misplaced-future',
    'relative-import',
    'deprecated-module',
    'import-star-module-level',

    'bad-builtin',

    'dict-iter-method',
    'dict-view-method',

    'long-suffix',
    'old-ne-operator',
    'old-octal-operator',
    'parameter-unpacking',

    'metaclass-assignment',
    'deprecated-module',

    'exception-message-attribute',
    'indexing-exception',
    'old-raise-syntax',
    'raising-string',
    'unpacking-in-except',
    # Enable the below test even if we do not want it, because of a memory leak if it's not enabled
    # See https://github.com/PyCQA/pylint/issues/1495#issuecomment-305724783
    # We will then ignore later the errors coming from this test, thanks to the `IGNORED_MESSAGE_IDS` list.
    'ungrouped-imports',
]

IGNORED_MESSAGE_IDS = [
    'C0412',
]

BAD_FUNCTIONS = [
    'apply',
    'cmp',
    'coerce',
    'execfile',
    'input',
    'intern',
    'long',
    'raw_input',
    'reload',
    'xrange',
    'long',
    'map',
    'filter',
    'zip',

    'file',
    'reduce',
]

BAD_MODULES = [
    'commands',
    'cPickle',
    'md5',
    'urllib',
    'urllib2',
    'urlparse',
    'sgmllib',
    'sha',
    'cgi',
    'htmlentitydefs',
    'HTMLParser',
    'Queue',
    'UserDict',
    'UserString',
    'UserList',
]

PUGIN_MODULES = [
    'pylint.extensions.bad_builtin',
]

paths = [tools.config['root_path']]
for module in get_modules():
    module_path = get_module_path(module)
    if not module_path.startswith(os.path.join(tools.config['root_path'], 'addons')):
        paths.append(module_path)

options = [
    '--disable=all',
    '--enable=%s' % ','.join(ENABLED_CODES),
    '--reports=n',
    "--msg-template='{msg} ({msg_id}) at {path}:{line}'",
    '--bad-functions=%s' % ','.join(BAD_FUNCTIONS),
    '--deprecated-modules=%s' % ','.join(BAD_MODULES),
]

MANAGER.astroid_cache = lrucache(150, MANAGER.astroid_cache.items())
reporter = Reporter()
linter = lint.PyLinter(reporter=reporter)
linter.load_default_plugins()
linter.load_plugin_modules(['pylint.extensions.bad_builtin'])
linter.load_command_line_configuration(options)

for path in paths:
    sys.path.append(path)
    linter.check(path)
error_messages = [message for message in reporter.messages if message['id'] not in IGNORED_MESSAGE_IDS]
if error_messages:
    out = '\n'.join('%s:%s (%s)%s' % (
        message['path'],
        message['line'],
        message['id'],
        message['message']) for message in error_messages if message['id'] not in IGNORED_MESSAGE_IDS)
    print out
    sys.exit(1)
