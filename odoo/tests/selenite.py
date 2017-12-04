# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import logging
import sys

from odoo.tools.which import which

_logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
    from selenium.webdriver.firefox.options import Options
except ImportError:
    _logger.warning('Selenium not installed, Http tests will be skipped')
    webdriver = None

SELENIUM_DRIVERS = ('chrome', 'chromium', 'firefox')


class SeleniteError(Exception):
    pass


class DriverSelect():
    """A callable object that returns a selenium driver"""

    def __init__(self, driver_name, driver_path=None, browser_path=None):
        self.driver_name = driver_name
        self.driver_path = driver_path
        self.browser_path = browser_path
        self._check_pathes()

    def __call__(self):
        if self.driver_name == 'chrome':
            return self._get_chrome()
        elif self.driver_name == 'chromium':
            return self._get_chrome(browser_name='chromium')
        elif self.driver_name == 'firefox':
            return self._get_firefox()

    def _get_chrome(self, browser_name=None):
        chrome_options = webdriver.ChromeOptions()
        if self.browser_path is not None:
            chrome_options.binary_location = self.browser_path
        chrome_options.set_headless()
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--window-size=1920,1080')
        desire = DesiredCapabilities.CHROME
        if browser_name:
            desire['browserName'] = browser_name
        desire['loggingPrefs'] = {'browser': 'ALL'}
        if self.driver_path:
            return webdriver.Chrome(self.driver_path, chrome_options=chrome_options, desired_capabilities=desire)
        else:
            return webdriver.Chrome(chrome_options=chrome_options, desired_capabilities=desire)

    def _get_firefox(self):
        __logger.warning("Firefox doesn't allow to fetch console log. Your tests are willing to fail.")
        firefox_capabilities = DesiredCapabilities.FIREFOX
        if not self.browser_path:
            self.browser_path = which('firefox')
        desire = DesiredCapabilities.FIREFOX
        options = Options()
        options.set_headless()
        binary = FirefoxBinary(self.browser_path)
        if self.driver_path:
            return webdriver.Firefox(executable_path=self.driver_path, firefox_binary=binary, firefox_options=options, log_path='/dev/null')
        else:
            return webdriver.Firefox(firefox_binary=binary, firefox_options=options)

    def _check_pathes(self):
        if self.driver_path and not os.path.exists(self.driver_path):
            raise SeleniteError("Driver not found")
        if self.browser_path and not os.path.exists(self.browser_path):
            raise SeleniteError("Browser not found")
