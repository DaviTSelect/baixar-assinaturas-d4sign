from pathlib import Path
from types import SimpleNamespace

import d4sign.processor as processor_module
from d4sign.processor import Processor

UUID = "12345678-1234-1234-1234-123456789abc"


class CacheNoMarker:
    def get_project(self, *_): return {}
    def contains(self, *_): return False
    def add(self, *_): pass


class CacheWithMarker(CacheNoMarker):
    def __init__(self):
        self.invalidated = []
    def mark_not_downloaded(self, project_id, uuid):
        self.invalidated.append((project_id, uuid))


def make_processor(tmp_path, driver=None, cache=None):
    cfg = SimpleNamespace(
        download_dir=tmp_path / "downloads",
        download_timeout=2,
        download_retries=1,
    )
    cfg.download_dir.mkdir(parents=True, exist_ok=True)
    browser = SimpleNamespace(driver=driver)
    return Processor(cfg, browser, SimpleNamespace(), cache or CacheNoMarker())


def test_duplicate_helpers_defensive_branches(tmp_path, monkeypatch):
    p = make_processor(tmp_path)

    class OldStat:
        st_mtime = 1.25
    assert p._mtime_ns(OldStat()) == 1_250_000_000

    # Hash de caminho inexistente cobre retorno defensivo.
    assert p._pdf_sha256(tmp_path / "nao-existe.pdf") is None

    # Adicionar sem índice prévio deve ser no-op.
    pdf = tmp_path / "fora.pdf"
    pdf.write_bytes(b"%PDF-x")
    p._add_to_pdf_index(pdf)
    assert not p._pdf_size_index

    # Candidato inválido/inexistente.
    assert p._find_duplicate_pdf(tmp_path / "ausente.pdf", tmp_path / "dest" / "x.pdf") is None

    # Cache sem mark_not_downloaded cobre o ramo não-callable.
    p._invalidate_cached_document("p", UUID)


def test_ensure_index_ignora_oserror(tmp_path, monkeypatch):
    p = make_processor(tmp_path)
    folder = tmp_path / "cofre"
    folder.mkdir()

    class BadPdf:
        def is_file(self): return True
        def resolve(self): return self
        def stat(self): raise OSError("stat")

    original_glob = Path.glob
    def fake_glob(self, pattern):
        if self.resolve() == folder.resolve():
            return iter([BadPdf()])
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", fake_glob)
    monkeypatch.setattr(processor_module, "is_pdf", lambda _: True)
    assert p._ensure_pdf_index(folder) == {}


def test_find_duplicate_hash_none_invalid_peer_e_inner_exception(tmp_path, monkeypatch):
    p = make_processor(tmp_path)
    folder = tmp_path / "cofre"
    folder.mkdir()
    candidate = folder / "candidate.pdf"
    candidate.write_bytes(b"%PDF-same")
    size = candidate.stat().st_size

    # Índice manual com peers suficientes para cobrir os caminhos defensivos.
    missing_peer = folder / "missing.pdf"
    weird_peer = object()
    p._pdf_size_index[folder.resolve()] = {
        size: {candidate.resolve(), missing_peer.resolve(), weird_peer}
    }

    # Hash indisponível => não há como declarar duplicidade.
    monkeypatch.setattr(p, "_pdf_sha256", lambda _: None)
    assert p._find_duplicate_pdf(candidate, folder / "dest.pdf") is None

    # Com hash do candidato disponível, peer ausente é ignorado e objeto inválido
    # cai no tratamento de TypeError interno.
    monkeypatch.setattr(p, "_pdf_sha256", lambda _: "hash")
    assert p._find_duplicate_pdf(candidate, folder / "dest.pdf") is None


def test_audit_unique_e_duplicate_externo(tmp_path):
    p = make_processor(tmp_path)
    folder = tmp_path / "cofre"
    folder.mkdir()

    only = folder / "only.pdf"
    only.write_bytes(b"%PDF-unique")
    audit = p._audit_expected_files({"u1": only})
    assert audit["complete"] is True
    assert audit["valid_unique"] == 1

    # Arquivo duplicado que não pertence ao mapa esperado cobre o par com nome.
    external = folder / "external.pdf"
    external.write_bytes(only.read_bytes())
    p._pdf_size_index.clear()
    p._pdf_hash_cache.clear()
    audit = p._audit_expected_files({"u1": only})
    assert audit["complete"] is False
    assert audit["duplicate_pairs"] == [("u1", "external.pdf")]


def test_process_specific_link_preview_e_auditoria_com_pendencias(tmp_path, monkeypatch, capsys):
    row = object()

    class Browser:
        def __init__(self): self.calls = 0
        def open_folder_page(self, project_id, page):
            self.calls += 1
            return [row] if self.calls == 1 else []

    cfg = SimpleNamespace(vault_uuid="e1334fa1-ccc7-4963-ae06-ec8ee1c93b62", download_dir=tmp_path / "downloads")
    p = Processor(cfg, Browser(), SimpleNamespace(), CacheNoMarker())

    monkeypatch.setattr(processor_module.DocumentParser, "uuid", staticmethod(lambda _: UUID))
    monkeypatch.setattr(processor_module.DocumentParser, "name", staticmethod(lambda _: ""))
    monkeypatch.setattr(p, "process_document", lambda **_: "downloaded")
    monkeypatch.setattr(
        p,
        "_audit_expected_files",
        lambda expected: {
            "expected": 1,
            "valid_unique": 0,
            "missing": [UUID],
            "duplicate_uuids": [UUID],
            "duplicate_pairs": [],
            "complete": False,
        },
    )

    stats = p.process_specific_link()
    out = capsys.readouterr().out
    assert stats.downloaded == 1
    assert "AUDITORIA FINAL" in out
    assert "UUIDs sem PDF válido" in out
    assert "UUIDs com conteúdo repetido" in out


def test_process_specific_link_preview_parser_exception(tmp_path, monkeypatch):
    row = object()

    class Browser:
        def __init__(self): self.calls = 0
        def open_folder_page(self, project_id, page):
            self.calls += 1
            return [row] if self.calls == 1 else []

    cfg = SimpleNamespace(vault_uuid="e1334fa1-ccc7-4963-ae06-ec8ee1c93b62", download_dir=tmp_path / "downloads")
    p = Processor(cfg, Browser(), SimpleNamespace(), CacheNoMarker())

    monkeypatch.setattr(processor_module.DocumentParser, "uuid", staticmethod(lambda _: (_ for _ in ()).throw(RuntimeError("preview"))))
    monkeypatch.setattr(p, "process_document", lambda **_: "error")
    stats = p.process_specific_link()
    assert stats.errors == 1
    assert p.last_audit["expected"] == 0


def test_process_document_duplicate_unlink_error(tmp_path, monkeypatch):
    cache = CacheWithMarker()
    p = make_processor(tmp_path, cache=cache)
    folder = tmp_path / "cofre"
    folder.mkdir()
    first = folder / "first.pdf"
    destination = folder / f"Doc - {UUID}.pdf"
    first.write_bytes(b"%PDF-repeat")
    destination.write_bytes(first.read_bytes())

    monkeypatch.setattr(processor_module.DocumentParser, "uuid", staticmethod(lambda _: UUID))
    monkeypatch.setattr(processor_module.DocumentParser, "name", staticmethod(lambda _: "Doc"))
    monkeypatch.setattr(processor_module.DocumentParser, "finalized", staticmethod(lambda _: True))

    original_unlink = Path.unlink
    def fake_unlink(self, *args, **kwargs):
        if self.resolve() == destination.resolve():
            raise OSError("locked")
        return original_unlink(self, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", fake_unlink)
    monkeypatch.setattr(p, "download_selenium", lambda **_: False)

    assert p.process_document(object(), folder, "p") == "error"
    assert ("p", UUID) in cache.invalidated


class MenuRow:
    def find_element(self, *args): return object()


class Link:
    def __init__(self, href="javascript: noop()"):
        self.href = href
    def get_attribute(self, name):
        return self.href if name == "href" else None


class Driver:
    def __init__(self, action=None): self.action = action
    def execute_script(self, script, *args):
        if self.action:
            self.action(script)


class Wait:
    def __init__(self, driver, timeout): self.driver = driver
    def until(self, condition): return Link()


def _patch_fast_download(monkeypatch):
    monkeypatch.setattr(processor_module, "WebDriverWait", Wait)
    monkeypatch.setattr(processor_module.DocumentParser, "download_element", staticmethod(lambda row: Link()))
    monkeypatch.setattr(processor_module.time, "sleep", lambda *_: None)


def test_download_invalid_pdf_unlink_error(tmp_path, monkeypatch):
    p = make_processor(tmp_path)
    download_dir = p.config.download_dir

    def action(script):
        if script == "noop()":
            (download_dir / "bad.pdf").write_bytes(b"NAO-PDF")
    p.browser.driver = Driver(action)
    _patch_fast_download(monkeypatch)

    original_is_pdf = processor_module.is_pdf
    monkeypatch.setattr(processor_module, "is_pdf", lambda path: False if Path(path).name == "bad.pdf" else original_is_pdf(path))

    original_unlink = Path.unlink
    def fake_unlink(self, *args, **kwargs):
        if self.name == "bad.pdf":
            raise OSError("locked")
        return original_unlink(self, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", fake_unlink)

    assert p.download_selenium(MenuRow(), tmp_path / "out" / "x.pdf") is False


def test_download_duplicate_temp_unlink_error(tmp_path, monkeypatch):
    p = make_processor(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    existing = folder / "existing.pdf"
    existing.write_bytes(b"%PDF-repeat")
    download_dir = p.config.download_dir

    def action(script):
        if script == "noop()":
            (download_dir / "dup.pdf").write_bytes(existing.read_bytes())
    p.browser.driver = Driver(action)
    _patch_fast_download(monkeypatch)

    original_unlink = Path.unlink
    def fake_unlink(self, *args, **kwargs):
        if self.name == "dup.pdf":
            raise OSError("locked")
        return original_unlink(self, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", fake_unlink)

    assert p.download_selenium(MenuRow(), folder / "dest.pdf") is False


def test_download_destino_final_invalido_cai_no_timeout(tmp_path, monkeypatch):
    p = make_processor(tmp_path)
    folder = tmp_path / "out"
    download_dir = p.config.download_dir
    destination = folder / "dest.pdf"

    def action(script):
        if script == "noop()":
            (download_dir / "ok.pdf").write_bytes(b"%PDF-valid")
    p.browser.driver = Driver(action)
    _patch_fast_download(monkeypatch)

    original_is_pdf = processor_module.is_pdf
    def fake_is_pdf(path):
        path = Path(path)
        if path.resolve() == destination.resolve():
            return False
        return original_is_pdf(path)
    monkeypatch.setattr(processor_module, "is_pdf", fake_is_pdf)

    assert p.download_selenium(MenuRow(), destination) is False
    assert destination.exists()


def test_download_duplicate_after_move_remove_e_unlink_error(tmp_path, monkeypatch):
    p = make_processor(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    existing = folder / "existing.pdf"
    existing.write_bytes(b"%PDF-existing")
    download_dir = p.config.download_dir
    destination = folder / "dest.pdf"

    def action(script):
        if script == "noop()":
            (download_dir / "candidate.pdf").write_bytes(b"%PDF-new")
    p.browser.driver = Driver(action)
    _patch_fast_download(monkeypatch)

    # Pré-movimento: diz que não há duplicado. Pós-movimento: força duplicado.
    calls = {"n": 0}
    def fake_find(candidate, dest):
        calls["n"] += 1
        return None if calls["n"] == 1 else existing
    monkeypatch.setattr(p, "_find_duplicate_pdf", fake_find)

    original_unlink = Path.unlink
    def fake_unlink(self, *args, **kwargs):
        if self.resolve() == destination.resolve():
            raise OSError("locked")
        return original_unlink(self, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", fake_unlink)

    assert p.download_selenium(MenuRow(), destination) is False


def test_process_specific_link_auditoria_incompleta_sem_listas(tmp_path, monkeypatch):
    class Browser:
        def open_folder_page(self, project_id, page): return []
    cfg = SimpleNamespace(vault_uuid="e1334fa1-ccc7-4963-ae06-ec8ee1c93b62", download_dir=tmp_path / "downloads")
    p = Processor(cfg, Browser(), SimpleNamespace(), CacheNoMarker())
    monkeypatch.setattr(
        p,
        "_audit_expected_files",
        lambda expected: {
            "expected": 0,
            "valid_unique": 0,
            "missing": [],
            "duplicate_uuids": [],
            "duplicate_pairs": [],
            "complete": False,
        },
    )
    stats = p.process_specific_link()
    assert stats.documents == 0
