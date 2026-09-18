import hashlib
import io
import json
from unittest.mock import Mock

import pytest

from d4sign import updates


def release(payload=b'installer'):
    return {"tag_name": "v99.0.0", "assets": [{
        "name": "D4Sign-Setup-99.0.0.exe",
        "browser_download_url": f"https://github.com/{updates.REPOSITORY}/releases/download/v99.0.0/D4Sign-Setup-99.0.0.exe",
        "size": len(payload), "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
    }]}


def serve(monkeypatch, data):
    monkeypatch.setattr(updates, "urlopen", lambda *args, **kwargs: io.BytesIO(json.dumps(data).encode()))


def test_new_stable_release(monkeypatch):
    serve(monkeypatch, release())
    assert updates.check_update().version == "v99.0.0"


@pytest.mark.parametrize("version", [updates.VERSION, "v0.0.0"])
def test_no_downgrade(monkeypatch, version):
    data = release()
    data["tag_name"] = version
    serve(monkeypatch, data)
    assert updates.check_update() is None


@pytest.mark.parametrize("field", ["draft", "prerelease"])
def test_reject_unstable(monkeypatch, field):
    data = release()
    data[field] = True
    serve(monkeypatch, data)
    with pytest.raises(ValueError):
        updates.check_update()


@pytest.mark.parametrize("field,value", [("digest", None), ("size", 0), ("browser_download_url", "https://evil.test/setup.exe"), ("name", "other.exe")])
def test_reject_bad_asset(monkeypatch, field, value):
    data = release()
    data["assets"][0][field] = value
    serve(monkeypatch, data)
    with pytest.raises(ValueError):
        updates.check_update()


@pytest.mark.parametrize("payload", [b'installer', b'changed!!', b'short', b'too long installer'])
def test_integrity_and_cleanup(monkeypatch, tmp_path, payload):
    serve(monkeypatch, release())
    update = updates.check_update()
    folder = tmp_path / "update"
    folder.mkdir()
    monkeypatch.setattr(updates.tempfile, "mkdtemp", lambda **kwargs: str(folder))
    monkeypatch.setattr(updates, "urlopen", lambda *args, **kwargs: io.BytesIO(payload))
    progress = Mock()
    if payload == b'installer':
        assert updates.download_update(update, progress).read_bytes() == payload
        progress.assert_called_with(100)
    else:
        with pytest.raises(ValueError):
            updates.download_update(update, progress)
        assert not folder.exists()


@pytest.mark.parametrize("version", [None, "1.2", "1.2.3-beta", "v01.2.3", "../1.2.3"])
def test_bad_versions(version):
    with pytest.raises(ValueError):
        updates.version_tuple(version)
