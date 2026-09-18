"""Stable GitHub releases and verified Windows installer downloads."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
from dataclasses import dataclass
from urllib.request import Request, urlopen

from .version import REPOSITORY, VERSION


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value):
        raise ValueError("Versão inválida; use vMAJOR.MINOR.PATCH.")
    return tuple(map(int, value.removeprefix("v").split(".")))


@dataclass(frozen=True)
class Update:
    version: str
    url: str
    size: int
    sha256: str


def request(url):
    return Request(url, headers={"User-Agent": "D4Sign-Desktop", "Accept": "application/vnd.github+json"})


def validate_url(url):
    prefix = f"https://github.com/{REPOSITORY}/releases/download/"
    if not isinstance(url, str) or not url.startswith(prefix):
        raise ValueError("Endereço do instalador inválido.")


def check_update():
    with urlopen(request(f"https://api.github.com/repos/{REPOSITORY}/releases/latest"), timeout=15) as response:
        release = json.load(response)
    if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
        raise ValueError("Release estável inválida.")
    tag = release.get("tag_name")
    if version_tuple(tag) <= version_tuple(VERSION):
        return None
    name = f"D4Sign-Setup-{tag.removeprefix('v')}.exe"
    for asset in release.get("assets", []):
        if asset.get("name") != name:
            continue
        validate_url(asset.get("browser_download_url"))
        digest = asset.get("digest", "")
        if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
            raise ValueError("Release sem SHA-256 válido. Publique novamente o instalador.")
        size = asset.get("size")
        if type(size) is not int or size <= 0:
            raise ValueError("Tamanho do instalador inválido.")
        return Update(tag, asset["browser_download_url"], size, digest[7:].lower())
    raise ValueError(f"Versão {tag} disponível, mas o instalador {name} ainda não foi publicado.")


def download_update(update, progress=lambda value: None):
    validate_url(update.url)
    folder = Path(tempfile.mkdtemp(prefix="d4sign-update-"))
    path = folder / "D4Sign-Setup.exe"
    digest = hashlib.sha256()
    received = 0
    try:
        with urlopen(request(update.url), timeout=60) as response, path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > update.size:
                    raise ValueError("Instalador maior que o tamanho informado.")
                output.write(chunk)
                digest.update(chunk)
                progress(int(received * 100 / update.size))
        if received != update.size or digest.hexdigest() != update.sha256:
            raise ValueError("A integridade do instalador não foi confirmada. Tente novamente.")
        return path
    except Exception:
        path.unlink(missing_ok=True)
        folder.rmdir()
        raise
