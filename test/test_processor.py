from pathlib import Path
from types import SimpleNamespace

import d4sign.processor as processor_module
from d4sign.models import Statistics
from d4sign.processor import Processor

UUID = "12345678-1234-1234-1234-123456789abc"
PROJECT_ID = "e1334fa1-ccc7-4963-ae06-ec8ee1c93b62"


class Cache:
    def __init__(self):
        self.downloaded = set()
        self.added = []
        self.invalidated = []
    def get_project(self, project_id):
        return {uuid: True for pid, uuid in self.downloaded if pid == project_id}
    def contains(self, project_id, uuid):
        return (project_id, uuid) in self.downloaded
    def add(self, project_id, uuid):
        self.downloaded.add((project_id, uuid))
        self.added.append((project_id, uuid))
    def mark_not_downloaded(self, project_id, uuid):
        self.downloaded.discard((project_id, uuid))
        self.invalidated.append((project_id, uuid))


class Browser:
    def __init__(self, pages=None, driver=None):
        self.pages = list(pages or [])
        self.driver = driver
    def open_folder_page(self, project_id, page):
        value = self.pages.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def make_processor(tmp_path: Path, pages=None, driver=None):
    config = SimpleNamespace(vault_uuid="e1334fa1-ccc7-4963-ae06-ec8ee1c93b62", download_dir=tmp_path / "downloads", download_timeout=5)
    browser = Browser(pages=pages, driver=driver)
    cache = Cache()
    return Processor(config, browser, SimpleNamespace(), cache), cache


def test_init_armazena_dependencias(tmp_path: Path):
    p, cache = make_processor(tmp_path)
    assert p.cache is cache
    assert p.config.download_dir == tmp_path / "downloads"


def test_process_specific_link_soma_todos_status(tmp_path: Path, monkeypatch):
    rows = [object(), object(), object(), object()]
    p, _ = make_processor(tmp_path, pages=[rows, []])
    results = iter(["downloaded", "cached", "skipped", "error"])
    monkeypatch.setattr(p, "process_document", lambda **kwargs: next(results))
    stats = p.process_specific_link()
    assert isinstance(stats, Statistics)
    assert (stats.pages, stats.documents, stats.downloaded, stats.cached, stats.skipped, stats.errors) == (1, 4, 1, 1, 1, 1)
    assert (tmp_path / "downloads" / "Cofre_Especifico").is_dir()


def test_process_specific_link_contabiliza_erro_de_navegacao(tmp_path: Path):
    p, _ = make_processor(tmp_path, pages=[RuntimeError("falha")])
    stats = p.process_specific_link()
    assert stats.errors == 1
    assert stats.pages == 0


def patch_parser(monkeypatch, uuid=UUID, name="Contrato", finalized=True):
    monkeypatch.setattr(processor_module.DocumentParser, "uuid", staticmethod(lambda row: uuid))
    monkeypatch.setattr(processor_module.DocumentParser, "name", staticmethod(lambda row: name))
    monkeypatch.setattr(processor_module.DocumentParser, "finalized", staticmethod(lambda row: finalized))


def test_process_document_sem_uuid(tmp_path: Path, monkeypatch):
    p, _ = make_processor(tmp_path)
    patch_parser(monkeypatch, uuid=None)
    assert p.process_document(object(), tmp_path, "p") == "error"


def test_process_document_cached(tmp_path: Path, monkeypatch):
    p, cache = make_processor(tmp_path)
    patch_parser(monkeypatch)
    cache.downloaded.add(("p", UUID))
    destination = tmp_path / f"Contrato - {UUID}.pdf"
    destination.write_bytes(b"%PDF-1.7\nexistente")
    assert p.process_document(object(), tmp_path, "p") == "cached"


def test_process_document_cache_sem_arquivo_forca_novo_download(tmp_path: Path, monkeypatch):
    p, cache = make_processor(tmp_path)
    patch_parser(monkeypatch)
    cache.downloaded.add(("p", UUID))

    def fake_download(row, destination):
        destination.write_bytes(b"%PDF-1.7\nrecuperado")
        return True

    monkeypatch.setattr(p, "download_selenium", fake_download)

    assert p.process_document(object(), tmp_path, "p") == "downloaded"
    assert ("p", UUID) in cache.invalidated
    assert ("p", UUID) in cache.added


def test_process_document_skipped(tmp_path: Path, monkeypatch):
    p, _ = make_processor(tmp_path)
    patch_parser(monkeypatch, finalized=False)
    assert p.process_document(object(), tmp_path, "p") == "skipped"


def test_process_document_pdf_existente_adiciona_cache(tmp_path: Path, monkeypatch):
    p, cache = make_processor(tmp_path)
    patch_parser(monkeypatch)
    destination = tmp_path / f"Contrato - {UUID}.pdf"
    destination.write_bytes(b"%PDF-1.7\nexistente")
    assert p.process_document(object(), tmp_path, "p") == "cached"
    assert ("p", UUID) in cache.added


def test_process_document_download_sucesso(tmp_path: Path, monkeypatch):
    p, cache = make_processor(tmp_path)
    patch_parser(monkeypatch)
    def fake_download(row, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"%PDF-1.7\nnovo")
        return True
    monkeypatch.setattr(p, "download_selenium", fake_download)
    assert p.process_document(object(), tmp_path, "p") == "downloaded"
    assert ("p", UUID) in cache.added


def test_process_document_download_falha(tmp_path: Path, monkeypatch):
    p, _ = make_processor(tmp_path)
    patch_parser(monkeypatch)
    monkeypatch.setattr(p, "download_selenium", lambda row, destination: False)
    assert p.process_document(object(), tmp_path, "p") == "error"


def test_download_selenium_processador(tmp_path: Path, monkeypatch):
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()

    class Menu:
        pass

    class Row:
        def find_element(self, by, selector):
            return Menu()

    class Link:
        def get_attribute(self, name):
            if name == "href":
                return "javascript: gerarPdf();"
            return None

    destination = tmp_path / "destino" / "doc.pdf"

    class Driver:
        def execute_script(self, script, *args):
            if script.strip() == "gerarPdf();":
                (download_dir / "baixado.pdf").write_bytes(b"%PDF-1.7\nconteudo")

    driver = Driver()
    p, _ = make_processor(tmp_path, driver=driver)

    class Wait:
        def __init__(self, driver, timeout):
            pass
        def until(self, condition):
            return Link()

    monkeypatch.setattr(processor_module, "WebDriverWait", Wait)
    monkeypatch.setattr(processor_module.time, "sleep", lambda *_: None)

    assert p.download_selenium(Row(), destination) is True
    assert destination.exists()


def test_download_selenium_usa_link_da_propria_linha_e_baixa_pdfs_diferentes(tmp_path: Path, monkeypatch):
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    output_dir = tmp_path / "destino"

    class Menu:
        pass

    class Link:
        def __init__(self, code):
            self.code = code
        def get_attribute(self, name):
            return f"javascript: {self.code}" if name == "href" else None

    class Row:
        def __init__(self, code):
            self.link = Link(code)
        def find_element(self, *args):
            return Menu()

    class Driver:
        def execute_script(self, script, *args):
            if script == "baixarA()":
                (download_dir / "a.pdf").write_bytes(b"%PDF-1.7\nA")
            elif script == "baixarB()":
                (download_dir / "b.pdf").write_bytes(b"%PDF-1.7\nB")

    class Wait:
        def __init__(self, driver, timeout):
            self.driver = driver
        def until(self, condition):
            return condition(self.driver)

    p, _ = make_processor(tmp_path, driver=Driver())
    p.config.download_retries = 1

    monkeypatch.setattr(processor_module, "WebDriverWait", Wait)
    monkeypatch.setattr(
        processor_module.DocumentParser,
        "download_element",
        staticmethod(lambda row: row.link),
    )
    monkeypatch.setattr(processor_module.time, "sleep", lambda *_: None)

    first = output_dir / "primeiro.pdf"
    second = output_dir / "segundo.pdf"

    assert p.download_selenium(Row("baixarA()"), first) is True
    assert p.download_selenium(Row("baixarB()"), second) is True
    assert first.read_bytes() != second.read_bytes()


def test_download_selenium_rejeita_pdf_duplicado_por_conteudo(tmp_path: Path, monkeypatch):
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    output_dir = tmp_path / "destino"
    output_dir.mkdir()

    existing = output_dir / "original.pdf"
    existing.write_bytes(b"%PDF-1.7\nMESMO-CONTEUDO")

    class Row:
        link = object()
        def find_element(self, *args):
            return object()

    class Link:
        def get_attribute(self, name):
            return "javascript: repetir()" if name == "href" else None

    class Driver:
        def execute_script(self, script, *args):
            if script == "repetir()":
                (download_dir / "duplicado.pdf").write_bytes(existing.read_bytes())

    class Wait:
        def __init__(self, driver, timeout):
            self.driver = driver
        def until(self, condition):
            return Link()

    p, _ = make_processor(tmp_path, driver=Driver())
    p.config.download_retries = 1

    monkeypatch.setattr(processor_module, "WebDriverWait", Wait)
    monkeypatch.setattr(processor_module.time, "sleep", lambda *_: None)

    destination = output_dir / "outro-uuid.pdf"
    assert p.download_selenium(Row(), destination) is False
    assert not destination.exists()
    assert existing.exists()


def test_process_document_repara_pdf_antigo_repetido(tmp_path: Path, monkeypatch):
    p, cache = make_processor(tmp_path)
    folder = tmp_path / "cofre"
    folder.mkdir()

    first_uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    second_uuid = UUID
    first = folder / f"Primeiro - {first_uuid}.pdf"
    second = folder / f"Contrato - {second_uuid}.pdf"
    repeated = b"%PDF-1.7\nPDF-ERRADO-REPETIDO"
    first.write_bytes(repeated)
    second.write_bytes(repeated)
    cache.downloaded.add(("p", second_uuid))

    patch_parser(monkeypatch, uuid=second_uuid, name="Contrato")

    def fake_download(row, destination):
        destination.write_bytes(b"%PDF-1.7\nPDF-CORRETO-SEGUNDO")
        return True

    monkeypatch.setattr(p, "download_selenium", fake_download)

    assert p.process_document(object(), folder, "p") == "downloaded"
    assert second.read_bytes() != first.read_bytes()
    assert ("p", second_uuid) in cache.invalidated


def test_auditoria_final_detecta_ausente_e_duplicados(tmp_path: Path):
    p, _ = make_processor(tmp_path)
    folder = tmp_path / "cofre"
    folder.mkdir()

    a = folder / "a.pdf"
    b = folder / "b.pdf"
    missing = folder / "missing.pdf"
    a.write_bytes(b"%PDF-1.7\nIGUAL")
    b.write_bytes(b"%PDF-1.7\nIGUAL")

    audit = p._audit_expected_files({"a": a, "b": b, "c": missing})

    assert audit["complete"] is False
    assert audit["missing"] == ["c"]
    assert audit["duplicate_uuids"] == ["a", "b"]
    assert audit["valid_unique"] == 0
