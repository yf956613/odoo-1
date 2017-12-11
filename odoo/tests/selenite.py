# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import logging
import tempfile

from odoo.tools.which import which

_logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
    from selenium.webdriver.firefox.options import Options
    from selenium.common.exceptions import WebDriverException, StaleElementReferenceException

except ImportError:
    _logger.warning('Selenium not installed, Http tests will be skipped')
    webdriver = None

SELENIUM_DRIVERS = ('chrome', 'chromium', 'firefox', 'phantomjs')


class SeleniteError(Exception):
    pass


class DriverSelect():
    """A callable object that returns a selenium driver"""

    def __init__(self, driver_name, driver_path=None, browser_path=None, headless=True):
        self.driver_name = driver_name
        self.driver_path = driver_path
        self.browser_path = browser_path
        self.headless = headless
        if not self.headless:
            _logger.warning('No headless mode !'.format(self.headless))
        self._check_pathes()

    def __call__(self):
        if webdriver is None:
            return None  # selenium not installed
        if self.driver_name == 'chrome':
            return self._get_chrome()
        elif self.driver_name == 'chromium':
            return self._get_chrome(browser_name='chromium')
        elif self.driver_name == 'firefox':
            return self._get_firefox()
        elif self.driver_name == 'phantomjs':
            return self._get_phantomjs()

    def _get_chrome(self, browser_name=None):
        chrome_options = webdriver.ChromeOptions()
        if self.browser_path is not None:
            chrome_options.binary_location = self.browser_path
        if self.headless:
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
        _logger.info("Firefox doesn't allow to fetch console log.")
        if not self.browser_path:
            self.browser_path = which('firefox')
        options = Options()
        if self.headless:
            options.set_headless()
        binary = FirefoxBinary(self.browser_path)
        if self.driver_path:
            driver = webdriver.Firefox(executable_path=self.driver_path, firefox_binary=binary, firefox_options=options, log_path='/dev/null')
        else:
            driver = webdriver.Firefox(firefox_binary=binary, firefox_options=options, log_path='/dev/null')
        driver.set_window_size(1920, 1080)
        return driver

    def _get_phantomjs(self):
        fd, cookies_file = tempfile.mkstemp(prefix='phantomjs_cookies')
        driver = webdriver.PhantomJS(service_args=['--cookies-file={}'.format(cookies_file)])
        driver.set_window_size(1920, 1080)
        return driver

    def _check_pathes(self):
        if self.driver_path and not os.path.exists(self.driver_path):
            raise SeleniteError("Driver not found")
        if self.browser_path and not os.path.exists(self.browser_path):
            raise SeleniteError("Browser not found")
