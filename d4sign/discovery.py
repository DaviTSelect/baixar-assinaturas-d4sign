"""Discover the sidebar without opening vault or document listing pages."""
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

from selenium.webdriver.support.ui import WebDriverWait

from .catalog import Location, selected_locations
from .utils import valid_uuid


def link_parts(href, base_url):
    url = urlsplit(urljoin(base_url, href))
    if url.netloc != urlsplit(base_url).netloc or url.scheme != 'https':
        return None
    path = url.path.rstrip('/').removesuffix('.html')
    parts = path.split('/')
    if len(parts) < 5 or parts[1:3] != ['desk', 'cofres'] or not parts[3].isdigit():
        return None
    if not all(valid_uuid(part) for part in parts[4:]):
        return None
    return parts[3], [part.lower() for part in parts[4:]], url._replace(query='', fragment='').geturl()


def parse_location_link(href, base_url):
    parsed = link_parts(href, base_url)
    return (parsed[0], parsed[1][-1]) if parsed else None


class SidebarParser(HTMLParser):
    """Read named liCofre/liFolder items, not favorite links or numeric IDs as UUIDs."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.records = []
        self.stack = []
        self.names = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'li':
            identity = attrs.get('id', '')
            record = None
            if re.fullmatch(r'li(?:Cofre|Folder)_\d+', identity):
                record = dict(id=identity, classes=attrs.get('class', '').split(), name='', href='', expandable=False,
                              parent=next((r['id'] for r in reversed(self.stack) if r), ''))
                self.records.append(record)
            self.stack.append(record)
        record = next((r for r in reversed(self.stack) if r), None)
        if not record:
            return
        if tag == 'a' and '/desk/cofres/' in attrs.get('href', ''):
            record['href'] = attrs['href']
            self.links.append(record)
        if tag == 'span':
            named = bool({'nome_cofre', 'nome_pasta'} & set(attrs.get('class', '').split()))
            self.names.append(record if named else None)
        action = attrs.get('onclick', '')
        if re.search(r'\b(?:o_subpastas|accordion_pastas(?:_shared)?)\s*\(', action):
            record['expandable'] = True

    def handle_endtag(self, tag):
        if tag == 'li' and self.stack:
            self.stack.pop()
        if tag == 'span' and self.names:
            self.names.pop()
        if tag == 'a' and self.links:
            self.links.pop()

    def handle_data(self, data):
        if self.names and self.names[-1]:
            self.names[-1]['name'] += data
        elif self.links:
            # Older D4Sign markup places the folder name directly in <a>,
            # without .nome_pasta (for example: "Aditivo - Carga Horária").
            text = data.strip()
            if text and not text.startswith('javascript:'):
                self.links[-1]['name'] += text + ' '


def sidebar_records(html):
    parser = SidebarParser()
    parser.feed(html)
    return parser.records


class CatalogDiscovery:
    def __init__(self, browser, progress=lambda message: None):
        self.browser, self.progress = browser, progress
        self.base = browser.config.base_url
        self.nodes = {}
        self.parents = {}
        self.roots = []

    def ready(self):
        driver = self.browser.current_driver
        WebDriverWait(driver, self.browser.config.page_timeout).until(
            lambda d: d.execute_script("return document.readyState === 'complete' && (!window.jQuery || jQuery.active === 0)")
        )
        if '/desk/' not in driver.current_url or driver.find_elements('css selector', 'input#Passwd'):
            raise RuntimeError('Sua sessao expirou. Saia e entre novamente.')

    def merge(self, records, expanded=None):
        fresh = set()
        for record in records:
            parsed = link_parts(record['href'], self.base)
            if not parsed or not record['name'].strip():
                raise RuntimeError('Nao foi possivel identificar um item do menu do D4Sign.')
            vault, chain, url = parsed
            key = f'{vault}:{chain[-1]}'
            if key not in self.nodes:
                node = Location(vault, chain[-1], record['name'].strip(), url=url,
                                dom_id=record['id'], loaded=not record['expandable'], expandable=record['expandable'])
                self.nodes[key] = node
                fresh.add(key)
            record['key'], record['chain'] = key, chain
        by_dom = {node.dom_id: node for node in self.nodes.values()}
        for record in records:
            node = self.nodes[record['key']]
            if record['id'].startswith('liCofre_'):
                if node not in self.roots:
                    self.roots.append(node)
                continue
            parent = by_dom.get(record['parent'])
            hints = [value for value in record['classes'] if value.startswith('liFolder_') and value != record['id']]
            if not parent and hints:
                parent = by_dom.get(hints[-1])
            if not parent and len(record['chain']) > 2:
                parent = self.nodes.get(f'{node.vault_id}:{record["chain"][-2]}')
            # Newly inserted sibling <li> elements belong to the branch just expanded.
            if not parent and expanded and node.key in fresh:
                parent = expanded
            if not parent:
                parent = self.nodes.get(f'{node.vault_id}:{record["chain"][0]}')
            if not parent or parent is node or parent.vault_id != node.vault_id:
                raise RuntimeError('Nao foi possivel determinar a pasta de origem de ' + node.name)
            if node.key in self.parents:
                continue
            ancestor = parent
            while ancestor:
                if ancestor is node:
                    raise RuntimeError('O menu retornou uma hierarquia circular.')
                ancestor = self.nodes.get(self.parents.get(ancestor.key))
            parent.children.append(node)
            self.parents[node.key] = parent.key
        # Root folders already present in the sidebar do not need a toggle/click.
        for root in self.roots:
            if root.children:
                root.loaded = True

    def load(self):
        self.browser.get(f'{self.base}/desk/')
        self.ready()
        self.nodes, self.parents, self.roots = {}, {}, []
        self.merge(sidebar_records(self.browser.current_driver.page_source))
        if not self.roots:
            raise RuntimeError('Nao foi possivel identificar os cofres no menu desta conta.')
        return self.roots

    def expand(self, key):
        node = self.nodes[key]
        if node.loaded:
            return node
        self.progress('Carregando subpastas de ' + node.name)
        self.ready()
        self.reveal(node)
        self.click_menu(node)
        self.merge(sidebar_records(self.browser.current_driver.page_source), expanded=node)
        node.loaded = True
        return node

    def reveal(self, node):
        """A document-page navigation can rebuild the sidebar with branches collapsed."""
        driver = self.browser.current_driver
        if driver.execute_script('return !!document.getElementById(arguments[0])', node.dom_id):
            return
        parent = self.nodes.get(self.parents.get(node.key))
        if not parent:
            raise RuntimeError('O menu mudou. Atualize a lista de cofres.')
        self.reveal(parent)
        self.click_menu(parent)

    def click_menu(self, node):
        clicked = self.browser.current_driver.execute_script("""
            const item = document.getElementById(arguments[0]);
            if (!item) return false;
            const controls = Array.from(item.querySelectorAll('[onclick]'));
            const control = controls.find(el => /(?:^|[;\\s:])(?:o_subpastas|accordion_pastas(?:_shared)?)\\s*\\(/.test(el.getAttribute('onclick')));
            if (!control) return false;
            control.click();
            return true;
        """, node.dom_id)
        if not clicked:
            raise RuntimeError('Nao foi possivel expandir ' + node.name + '. Atualize a lista.')
        self.ready()
        # Wait for AJAX and menu mutations to settle; never navigate into a vault.
        last, stable = None, 0
        def settled(driver):
            nonlocal last, stable
            if not driver.execute_script('return !window.jQuery || jQuery.active === 0'):
                stable = 0
                return False
            html = driver.page_source
            stable = stable + 1 if html == last else 0
            last = html
            return stable >= 2
        WebDriverWait(self.browser.current_driver, self.browser.config.page_timeout, poll_frequency=0.3).until(settled)

    def materialize(self, selected, recursive):
        if not recursive:
            return
        pending = selected_locations(self.roots, selected, False)
        visited = set()
        while pending:
            node = pending.pop(0)
            if node.key in visited:
                continue
            visited.add(node.key)
            self.expand(node.key)
            pending.extend(node.children)
