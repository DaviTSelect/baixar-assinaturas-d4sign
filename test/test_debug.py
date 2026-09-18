from pathlib import Path

import d4sign.debug as debug_module
from d4sign.debug import Debugger


class Driver:
    current_url = "https://example.test/pagina"
    title = "Página"
    page_source = "<html><body>Texto</body></html>"

    def __init__(self):
        self.screenshots = []
        self.scripts = []
        self.elements = []

    def execute_script(self, script, *args):
        self.scripts.append((script, args))
        if "return document.readyState" in script:
            return "complete"
        if "querySelectorAll" in script:
            return {"trs": 2, "links": 3, "buttons": 1, "inputs": 4, "divs": 5, "bodyText": "corpo"}
        if "innerText" in script:
            return "Texto do body"
        return None

    def save_screenshot(self, path):
        self.screenshots.append(path)
        Path(path).write_bytes(b"PNG")
        return True

    def find_elements(self, by, selector):
        return self.elements


class Element:
    text = "Elemento"

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True


def test_init_cria_diretorio(tmp_path: Path):
    directory = tmp_path / "debug"
    dbg = Debugger(Driver(), directory=directory)
    assert dbg.directory == directory
    assert directory.is_dir()


def test_log_separator_e_disabled(tmp_path: Path, capsys):
    dbg = Debugger(Driver(), directory=tmp_path)
    dbg.log("mensagem")
    dbg.separator("titulo")
    out = capsys.readouterr().out
    assert "[DEBUG] mensagem" in out
    assert "[DEBUG] titulo" in out

    off = Debugger(Driver(), enabled=False, directory=tmp_path / "off")
    off.log("não aparece")
    off.separator("não aparece")
    assert "não aparece" not in capsys.readouterr().out


def test_page_info(tmp_path: Path, capsys):
    dbg = Debugger(Driver(), directory=tmp_path)
    dbg.page_info()
    out = capsys.readouterr().out
    assert "URL: https://example.test/pagina" in out
    assert "READY STATE: complete" in out


def test_inspect_dom(tmp_path: Path, capsys):
    dbg = Debugger(Driver(), directory=tmp_path)
    dbg.inspect_dom()
    out = capsys.readouterr().out
    assert "TR: 2" in out
    assert "corpo" in out


def test_save_state_cria_arquivos(tmp_path: Path, monkeypatch):
    driver = Driver()
    dbg = Debugger(driver, directory=tmp_path)

    class FixedDatetime:
        @classmethod
        def now(cls):
            class D:
                def strftime(self, fmt):
                    return "20260903_120000_000000"
            return D()

    monkeypatch.setattr(debug_module, "datetime", FixedDatetime)
    dbg.save_state("estado teste")

    prefix = tmp_path / "20260903_120000_000000_estado_teste"
    assert prefix.with_suffix(".png").exists()
    assert prefix.with_suffix(".html").read_text(encoding="utf-8") == driver.page_source
    assert prefix.with_suffix(".txt").read_text(encoding="utf-8") == "Texto do body"


def test_inspect_elements(tmp_path: Path, capsys):
    driver = Driver()
    driver.elements = [Element(), Element()]
    dbg = Debugger(driver, directory=tmp_path)
    result = dbg.inspect_elements(".item", "Itens")
    assert result == driver.elements
    assert "2 elemento(s)" in capsys.readouterr().out


def test_inspect_elements_disabled(tmp_path: Path):
    dbg = Debugger(Driver(), enabled=False, directory=tmp_path)
    assert dbg.inspect_elements(".item") == []


def test_scroll_to(tmp_path: Path, monkeypatch):
    driver = Driver()
    dbg = Debugger(driver, directory=tmp_path)
    monkeypatch.setattr(debug_module.time, "sleep", lambda *_: None)
    element = object()
    dbg.scroll_to(element)
    assert any(args == (element,) for _, args in driver.scripts)
