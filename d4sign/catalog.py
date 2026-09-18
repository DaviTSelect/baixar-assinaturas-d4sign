"""Account locations and deterministic local folder layout."""
from dataclasses import dataclass, field
from pathlib import Path
import re

from .utils import sanitize_filename


@dataclass
class Location:
    vault_id: str
    uuid: str
    name: str
    children: list['Location'] = field(default_factory=list)
    url: str = ''
    dom_id: str = ''
    loaded: bool = True
    expandable: bool = False

    @property
    def key(self):
        return f'{self.vault_id}:{self.uuid}'


def directory_name(name):
    value = sanitize_filename(name)
    if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', value, re.I):
        value = '_' + value
    return value


def location_paths(roots):
    """Keep names, disambiguating Windows case/sanitization collisions."""
    result = {}
    def visit(nodes, parent):
        used = set()
        for node in sorted(nodes, key=lambda item: (item.name.casefold(), item.key)):
            base = directory_name(node.name)
            name, index = base, 2
            while name.casefold() in used:
                name = f'{base} ({index})'
                index += 1
            used.add(name.casefold())
            path = parent / name
            result[node.key] = path
            visit(node.children, path)
    visit(roots, Path())
    return result


def selected_locations(roots, selected, recursive=True):
    """Expand selected subtrees once, preserving their full account paths."""
    result = []
    def visit(node, inherited=False):
        included = inherited or node.key in selected
        if included:
            result.append(node)
        for child in node.children:
            visit(child, included and recursive)
    for root in roots:
        visit(root)
    return result
