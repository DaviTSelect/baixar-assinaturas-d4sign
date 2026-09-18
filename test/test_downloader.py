from pathlib import Path
from types import SimpleNamespace

import requests
from selenium.common.exceptions import WebDriverException

import d4sign.downloader as downloader_module
from d4sign.downloader import Downloader
from d4sign.models import Document


def make_config(tmp_path: Path, **overrides):
    data = dict(
        download_dir=tmp_path / "downloads",
        download_timeout=5,
        download_retries=2,
        retry_delay=0,
        debug=False,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


class Driver:
    current_url = "https://example.test/desk/doc"
    title = "Documento"

    def __init__(self):
        self.cookies = [{"name": "sid", "value": "abc", "domain": "example.test", "path": "/"}]
        self.scripts = []
        self.rows_by_selector = {}

    def execute_script(self, script, *args):
        self.scripts.append((script, args))
        if "readyState" in script:
            return "complete"
        if "scrollHeight" in script:
            return 2000
        if "innerText" in script:
            return "corpo da página"
        return None

    def find_elements(self, by, selector):
        value = self.rows_by_selector.get(selector, [])
        if isinstance(value, Exception):
            raise value
        return value

    def get_cookies(self):
        return self.cookies


class Browser:
    def __init__(self, driver):
        self.current_driver = driver


class Element:
    def __init__(self, text="", attrs=None, displayed=True, click_error=None):
        self.text = text
        self.attrs = attrs or {}
        self.displayed = displayed
        self.click_error = click_error
        self.clicked = False

    def get_attribute(self, name):
        return self.attrs.get(name)

    def is_displayed(self):
        return self.displayed

    def click(self):
        if self.click_error:
            raise self.click_error
        self.clicked = True


class Row:
    def __init__(self, mapping=None, outer_html=""):
        self.mapping = mapping or {}
        self.outer_html = outer_html

    def find_elements(self, by, selector):
        value = self.mapping.get(selector, [])
        if isinstance(value, Exception):
            raise value
        return value

    def get_attribute(self, name):
        return self.outer_html if name == "outerHTML" else None


def make_downloader(tmp_path: Path, **config_overrides):
    driver = Driver()
    downloader = Downloader(make_config(tmp_path, **config_overrides), Browser(driver))
    return downloader, driver


def test_init_debug_flag_log_debug_exception_driver(tmp_path: Path, capsys):
    downloader, driver = make_downloader(tmp_path, debug="sim")
    assert downloader.debug_enabled is True
    assert downloader.driver is driver
    downloader.log("normal")
    downloader.debug("detalhe")
    downloader.debug_exception("falhou", ValueError("x"))
    out = capsys.readouterr().out
    assert "[D4SIGN] normal" in out
    assert "[DEBUG] detalhe" in out
    assert "ValueError: x" in out


def test_get_debug_flag_booleano_e_fallback(tmp_path: Path):
    d, _ = make_downloader(tmp_path, debug=True)
    assert d._get_debug_flag() is True
    d.config.debug = False
    assert d._get_debug_flag() is False


def test_wait_document_ready_complete(tmp_path: Path, monkeypatch):
    downloader, _ = make_downloader(tmp_path)
    monkeypatch.setattr(downloader_module.time, "sleep", lambda *_: None)
    assert downloader.wait_document_ready(timeout=1) is True


def test_debug_page_executa_com_debug(tmp_path: Path, capsys):
    downloader, driver = make_downloader(tmp_path, debug=True)
    driver.rows_by_selector["tr"] = [1, 2]
    downloader.debug_page()
    out = capsys.readouterr().out
    assert "TRs: 2" in out
    assert "BODY: corpo da página" in out


def test_scroll_page_executa_scripts(tmp_path: Path, monkeypatch):
    downloader, driver = make_downloader(tmp_path)
    monkeypatch.setattr(downloader_module.time, "sleep", lambda *_: None)
    downloader.scroll_page()
    assert len(driver.scripts) >= 3


def test_find_document_rows_primeiro_selector_com_resultado(tmp_path: Path):
    downloader, driver = make_downloader(tmp_path)
    rows = [object()]
    driver.rows_by_selector["table tbody tr"] = rows
    assert downloader.find_document_rows() == rows


def test_wait_for_documents_retorna_quando_quantidade_estabiliza(tmp_path: Path, monkeypatch):
    downloader, _ = make_downloader(tmp_path)
    rows = [object(), object()]
    monkeypatch.setattr(downloader, "wait_document_ready", lambda timeout=5: True)
    monkeypatch.setattr(downloader, "scroll_page", lambda: None)
    monkeypatch.setattr(downloader, "find_document_rows", lambda: rows)
    monkeypatch.setattr(downloader_module.time, "sleep", lambda *_: None)
    counter = {"n": 0}
    def fake_time():
        counter["n"] += 0.1
        return counter["n"]
    monkeypatch.setattr(downloader_module.time, "time", fake_time)
    assert downloader.wait_for_documents(max_wait=10, stable_checks=2) == rows


def test_sync_cookies_e_headers(tmp_path: Path):
    downloader, _ = make_downloader(tmp_path)
    downloader.sync_cookies()
    assert downloader.session.cookies.get("sid") == "abc"
    headers = downloader._headers()
    assert headers["Referer"] == "https://example.test/desk/doc"
    assert "application/pdf" in headers["Accept"]


def test_extract_download_url_por_link(tmp_path: Path):
    downloader, _ = make_downloader(tmp_path)
    link = Element(text="Baixar", attrs={"href": "https://example.test/download/doc.pdf"})
    row = Row({"a": [link]})
    assert downloader.extract_download_url(row) == "https://example.test/download/doc.pdf"


def test_extract_download_url_fallback_html(tmp_path: Path):
    downloader, _ = make_downloader(tmp_path)
    row = Row(outer_html='<tr data-url="https://example.test/files/doc.pdf"></tr>')
    assert downloader.extract_download_url(row) == "https://example.test/files/doc.pdf"


def test_find_download_button_visivel(tmp_path: Path):
    downloader, _ = make_downloader(tmp_path)
    button = Element(text="Download", displayed=True)
    # Primeiro seletor XPath da implementação.
    first_selector = downloader_module.By.XPATH
    class AnyRow:
        def find_elements(self, by, selector):
            return [button] if by == first_selector else []
    assert downloader.find_download_button(AnyRow()) is button


def test_download_http_pdf_valido(tmp_path: Path, monkeypatch):
    downloader, _ = make_downloader(tmp_path)
    response = SimpleNamespace(
        status_code=200,
        url="https://example.test/final.pdf",
        headers={"Content-Type": "application/pdf"},
        content=b"%PDF-1.7\nconteudo",
        text="",
    )
    monkeypatch.setattr(downloader, "sync_cookies", lambda: None)
    monkeypatch.setattr(downloader.session, "get", lambda *args, **kwargs: response)
    dest = tmp_path / "saida" / "doc.pdf"
    assert downloader.download_http("https://example.test/doc", dest) is True
    assert dest.exists()


def test_download_http_status_invalido_e_request_exception(tmp_path: Path, monkeypatch):
    downloader, _ = make_downloader(tmp_path)
    monkeypatch.setattr(downloader, "sync_cookies", lambda: None)
    response = SimpleNamespace(status_code=403, url="x", headers={}, content=b"", text="")
    monkeypatch.setattr(downloader.session, "get", lambda *args, **kwargs: response)
    assert downloader.download_http("https://x", tmp_path / "a.pdf") is False

    def fail(*args, **kwargs):
        raise requests.RequestException("rede")
    monkeypatch.setattr(downloader.session, "get", fail)
    assert downloader.download_http("https://x", tmp_path / "b.pdf") is False


def test_list_files_e_cleanup_temporary_files(tmp_path: Path, capsys):
    downloader, _ = make_downloader(tmp_path, debug=True)
    directory = tmp_path / "arquivos"
    directory.mkdir()
    (directory / "a.pdf").write_bytes(b"%PDF-x")
    (directory / "b.crdownload").write_bytes(b"temp")
    assert {p.name for p in downloader.list_files(directory)} == {"a.pdf", "b.crdownload"}
    downloader.cleanup_temporary_files(directory)
    assert "b.crdownload" in capsys.readouterr().out
    assert downloader.list_files(tmp_path / "inexistente") == []


def test_wait_for_download_detecta_pdf_estavel(tmp_path: Path, monkeypatch):
    downloader, _ = make_downloader(tmp_path)
    directory = tmp_path / "downloads"
    directory.mkdir()
    pdf = directory / "novo.pdf"
    pdf.write_bytes(b"%PDF-1.7\nconteudo")
    monkeypatch.setattr(downloader_module.time, "sleep", lambda *_: None)
    counter = {"n": 0}
    def fake_time():
        counter["n"] += 0.1
        return counter["n"]
    monkeypatch.setattr(downloader_module.time, "time", fake_time)
    assert downloader.wait_for_download(directory, before=set(), timeout=5) == pdf


def test_download_selenium_move_pdf_para_destino(tmp_path: Path, monkeypatch):
    downloader, driver = make_downloader(tmp_path)
    source_dir = downloader.config.download_dir
    source_dir.mkdir(parents=True)
    downloaded = source_dir / "temporario.pdf"
    downloaded.write_bytes(b"%PDF-1.7\nconteudo")
    button = Element(text="Download")
    monkeypatch.setattr(downloader, "find_download_button", lambda row: button)
    monkeypatch.setattr(downloader, "wait_for_download", lambda directory, before: downloaded)
    monkeypatch.setattr(downloader_module.time, "sleep", lambda *_: None)
    destination = tmp_path / "final" / "documento.pdf"
    assert downloader.download_selenium(Row(), destination) is True
    assert destination.exists()
    assert not downloaded.exists()


def test_download_document_cache_http_e_fallback(tmp_path: Path, monkeypatch):
    downloader, _ = make_downloader(tmp_path)
    doc = Document(uuid="u", name="Doc", download_url="https://example.test/doc.pdf")
    destination = tmp_path / "doc.pdf"
    destination.write_bytes(b"%PDF-1.7\ncache")
    assert downloader.download_document(Row(), doc, destination) is True

    destination.unlink()
    monkeypatch.setattr(downloader, "download_http", lambda url, dest: True)
    assert downloader.download_document(Row(), doc, destination) is True

    doc_no_url = Document(uuid="u", name="Doc", download_url=None)
    monkeypatch.setattr(downloader, "extract_download_url", lambda row: None)
    monkeypatch.setattr(downloader, "download_selenium", lambda row, dest: True)
    assert downloader.download_document(Row(), doc_no_url, destination) is True


def test_build_destination_sanitiza_e_adiciona_pdf(tmp_path: Path):
    downloader, _ = make_downloader(tmp_path)
    path = downloader.build_destination(" Pasta: 1 ", " contrato? ")
    assert path == downloader.config.download_dir / "Pasta_ 1" / "contrato_.pdf"
    path2 = downloader.build_destination("Pasta", "arquivo.PDF")
    assert path2.name == "arquivo.PDF"
