"""Configuração compartilhada dos testes.

Os testes usam Selenium apenas por interface (mocks/fakes). Para permitir executar
os testes unitários até em uma máquina sem Selenium instalado, este arquivo cria
shims mínimos somente quando os pacotes reais não estão disponíveis.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _install_selenium_shim() -> None:
    try:
        import selenium  # noqa: F401
        return
    except ImportError:
        pass

    selenium = types.ModuleType("selenium")
    webdriver = types.ModuleType("selenium.webdriver")
    common = types.ModuleType("selenium.common")
    exceptions = types.ModuleType("selenium.common.exceptions")
    chrome = types.ModuleType("selenium.webdriver.chrome")
    chrome_options = types.ModuleType("selenium.webdriver.chrome.options")
    chrome_service = types.ModuleType("selenium.webdriver.chrome.service")
    webdriver_common = types.ModuleType("selenium.webdriver.common")
    by_module = types.ModuleType("selenium.webdriver.common.by")
    support = types.ModuleType("selenium.webdriver.support")
    ui_module = types.ModuleType("selenium.webdriver.support.ui")
    ec_module = types.ModuleType("selenium.webdriver.support.expected_conditions")

    class WebDriverException(Exception):
        pass

    class TimeoutException(WebDriverException):
        pass

    class NoSuchElementException(WebDriverException):
        pass

    class StaleElementReferenceException(WebDriverException):
        pass

    class By:
        ID = "id"
        NAME = "name"
        CSS_SELECTOR = "css selector"
        XPATH = "xpath"
        TAG_NAME = "tag name"

    class Options:
        def __init__(self):
            self.arguments = []
            self.experimental_options = {}

        def add_argument(self, value):
            self.arguments.append(value)

        def add_experimental_option(self, name, value):
            self.experimental_options[name] = value

    class Service:
        def __init__(self, executable_path=None, *args, **kwargs):
            self.executable_path = executable_path

    class WebDriverWait:
        def __init__(self, driver, timeout):
            self.driver = driver
            self.timeout = timeout

        def until(self, condition):
            result = condition(self.driver) if callable(condition) else condition
            if result:
                return result
            raise TimeoutException("condition not met")

    def presence_of_element_located(locator):
        def _predicate(driver):
            try:
                return driver.find_element(*locator)
            except Exception:
                return False
        return _predicate

    class _ChromePlaceholder:
        pass

    webdriver.Chrome = _ChromePlaceholder
    exceptions.WebDriverException = WebDriverException
    exceptions.TimeoutException = TimeoutException
    exceptions.NoSuchElementException = NoSuchElementException
    exceptions.StaleElementReferenceException = StaleElementReferenceException
    by_module.By = By
    chrome_options.Options = Options
    chrome_service.Service = Service
    ui_module.WebDriverWait = WebDriverWait
    ec_module.presence_of_element_located = presence_of_element_located
    support.expected_conditions = ec_module

    sys.modules.update({
        "selenium": selenium,
        "selenium.webdriver": webdriver,
        "selenium.common": common,
        "selenium.common.exceptions": exceptions,
        "selenium.webdriver.chrome": chrome,
        "selenium.webdriver.chrome.options": chrome_options,
        "selenium.webdriver.chrome.service": chrome_service,
        "selenium.webdriver.common": webdriver_common,
        "selenium.webdriver.common.by": by_module,
        "selenium.webdriver.support": support,
        "selenium.webdriver.support.ui": ui_module,
        "selenium.webdriver.support.expected_conditions": ec_module,
    })


def _install_webdriver_manager_shim() -> None:
    try:
        import webdriver_manager.chrome  # noqa: F401
        return
    except ImportError:
        pass

    manager = types.ModuleType("webdriver_manager")
    chrome = types.ModuleType("webdriver_manager.chrome")

    class ChromeDriverManager:
        def install(self):
            return "chromedriver"

    chrome.ChromeDriverManager = ChromeDriverManager
    sys.modules["webdriver_manager"] = manager
    sys.modules["webdriver_manager.chrome"] = chrome


_install_selenium_shim()
_install_webdriver_manager_shim()
