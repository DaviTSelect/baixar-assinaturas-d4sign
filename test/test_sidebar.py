from pathlib import Path
from unittest.mock import Mock
from dataclasses import replace

import pytest

from d4sign.discovery import CatalogDiscovery, sidebar_records, parse_location_link
from d4sign.desktop import desktop_config
from d4sign.browser import D4SignBrowser
from d4sign.catalog import location_paths
from d4sign import browser as browser_module

BASE = 'https://secure.d4sign.com.br'
VAULT = '7e36e454-8980-4d85-9127-f760f507a28a'
FOLDER = 'a9ba1613-9b6e-47a1-8ec6-1cabad35f6c5'
LEAF = '33333333-3333-3333-3333-333333333333'
HTML = (Path(__file__).parent / 'fixtures/sidebar.html').read_text(encoding='utf-8')
LEAF_HTML = f'''<li id="liFolder_999" class="liCofre_782090 liFolder_768854 liFolder_999">
    <a href="/desk/cofres/782090/{VAULT}/{LEAF}.html"><span class="nome_pasta">2026</span></a></li>'''


def discovery(monkeypatch, tmp_path):
    browser = Mock(config=desktop_config('a', 'b', str(tmp_path)))
    browser.current_driver.page_source = HTML
    catalog = CatalogDiscovery(browser)
    monkeypatch.setattr(catalog, 'ready', lambda: None)
    return catalog, browser


def test_real_sidebar_html_links_and_sibling_hierarchy(monkeypatch, tmp_path):
    catalog, browser = discovery(monkeypatch, tmp_path)
    roots = catalog.load()
    browser.get.assert_called_once_with(BASE + '/desk/')
    browser.current_driver.execute_script.assert_not_called()
    assert len(roots) == 1
    root = roots[0]
    assert root.name == 'Recursos Humanos'
    assert root.dom_id == 'liCofre_782090'
    assert root.uuid == VAULT and root.loaded
    child = root.children[0]
    assert child.name == 'Aditivo' and child.uuid == FOLDER
    assert child.dom_id == 'liFolder_768854'
    assert child.url == f'{BASE}/desk/cofres/782090/{VAULT}/{FOLDER}.html'
    assert not child.loaded


def test_folder_name_directly_in_anchor_is_supported():
    html = f'''<li id="liFolder_1142255" class="liCofre_782090 liFolder_1142255">
      <div class="folders_list"><i onclick="o_subpastas('782090','{VAULT}','02a03294-c622-4d84-88f8-8d1dc38e52ee')"></i>
      <a href="/desk/cofres/782090/{VAULT}/02a03294-c622-4d84-88f8-8d1dc38e52ee.html"> Aditivo - Carga Horária </a></div></li>'''
    records = sidebar_records(html)
    assert records[0]['name'].strip() == 'Aditivo - Carga Horária'
    assert records[0]['href'].endswith('02a03294-c622-4d84-88f8-8d1dc38e52ee.html')


def test_folder_link_preserves_root_and_folder():
    assert parse_location_link(f'/desk/cofres/782090/{VAULT}/{FOLDER}.html?p=0', BASE) == ('782090', FOLDER)
    assert parse_location_link(f'https://evil.test/desk/cofres/782090/{VAULT}/{FOLDER}.html', BASE) is None


def test_expand_clicks_only_requested_menu_branch(monkeypatch, tmp_path):
    catalog, browser = discovery(monkeypatch, tmp_path)
    catalog.load()
    browser.get.reset_mock()
    def execute(script, *args):
        if 'control.click()' in script:
            assert args == ('liFolder_768854',)
            assert 'control.click()' in script
            browser.current_driver.page_source = HTML + LEAF_HTML
        return True
    browser.current_driver.execute_script.side_effect = execute
    node = catalog.expand('782090:' + FOLDER)
    assert node.loaded
    assert node.children[0].uuid == LEAF
    browser.get.assert_not_called()
    assert location_paths(catalog.roots)['782090:' + LEAF].parts == ('Recursos Humanos', 'Aditivo', '2026')
    browser.current_driver.execute_script.reset_mock()
    catalog.expand(node.key)
    browser.current_driver.execute_script.assert_not_called()


def test_no_recursive_scan_without_download_or_expand(monkeypatch, tmp_path):
    catalog, browser = discovery(monkeypatch, tmp_path)
    catalog.load()
    catalog.expand = Mock()
    catalog.materialize(['782090:' + VAULT], False)
    catalog.expand.assert_not_called()
    catalog.materialize(['782090:' + FOLDER], True)
    catalog.expand.assert_called_once_with('782090:' + FOLDER)


def test_known_numeric_parent_class_beats_vault_prefix(monkeypatch, tmp_path):
    catalog, browser = discovery(monkeypatch, tmp_path)
    browser.current_driver.page_source = HTML + LEAF_HTML
    roots = catalog.load()
    assert len(roots[0].children) == 1
    assert roots[0].children[0].children[0].name == '2026'


def test_missing_expander_is_error_not_empty_folder(monkeypatch, tmp_path):
    catalog, browser = discovery(monkeypatch, tmp_path)
    catalog.load()
    browser.current_driver.execute_script.side_effect = lambda script, *args: 'control.click()' not in script
    with pytest.raises(RuntimeError, match='expandir'):
        catalog.expand('782090:' + FOLDER)
    assert not catalog.nodes['782090:' + FOLDER].loaded


def test_download_uses_exact_sidebar_folder_address(monkeypatch, tmp_path):
    url = f'{BASE}/desk/cofres/782090/{VAULT}/{FOLDER}.html'
    config = replace(desktop_config('a', 'b', str(tmp_path)), location_url=url)
    browser = D4SignBrowser(config)
    driver = Mock(current_url=url)
    browser.driver = driver
    driver.find_elements.return_value = []
    driver.execute_script.return_value = 'complete'
    monkeypatch.setattr(browser, 'get', Mock())
    monkeypatch.setattr(browser_module.time, 'sleep', lambda _: None)
    browser.open_folder_page(FOLDER, 2)
    browser.get.assert_called_once_with(url + '?p=2&f=')
