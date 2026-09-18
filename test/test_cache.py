import json
from pathlib import Path

from d4sign.cache import Cache


def test_cache_init_sem_arquivo(tmp_path: Path):
    cache = Cache(tmp_path / "cache.json")
    assert cache.data == {}


def test_cache_load_normaliza_dados(tmp_path: Path):
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({" 1 ": {" u1 ": 1, "": True}, "2": [1, 2]}), encoding="utf-8")
    cache = Cache(path)
    assert cache.data == {"1": {"u1": True}, "2": {}}


def test_cache_load_json_invalido_gera_cache_vazio(tmp_path: Path, capsys):
    path = tmp_path / "cache.json"
    path.write_text("{invalido", encoding="utf-8")
    cache = Cache(path)
    assert cache.data == {}
    assert "Não foi possível carregar" in capsys.readouterr().out


def test_cache_save_persiste_atomico(tmp_path: Path):
    path = tmp_path / "nested" / "cache.json"
    cache = Cache(path)
    cache.data = {"p": {"u": True}}
    cache.save()
    assert json.loads(path.read_text(encoding="utf-8")) == {"p": {"u": True}}
    assert not path.with_suffix(".tmp").exists()


def test_chaves_normalizadas():
    assert Cache._project_key(" 10 ") == "10"
    assert Cache._uuid_key(" u1 ") == "u1"


def test_status_contains_get_status_e_add(tmp_path: Path):
    cache = Cache(tmp_path / "cache.json")
    assert cache.is_downloaded("p", "u") is False
    assert cache.contains("p", "u") is False
    cache.add(" p ", " u ")
    assert cache.is_downloaded("p", "u") is True
    assert cache.contains("p", "u") is True
    assert cache.get_status("p", "u") is True


def test_set_status_uuid_vazio_nao_salva(tmp_path: Path):
    cache = Cache(tmp_path / "cache.json")
    cache.set_status("p", "   ", True)
    assert cache.data == {}
    assert not cache.cache_file.exists()


def test_mark_downloaded_e_mark_not_downloaded(tmp_path: Path):
    cache = Cache(tmp_path / "cache.json")
    cache.mark_downloaded("p", "u")
    assert cache.get_status("p", "u") is True
    cache.mark_not_downloaded("p", "u")
    assert cache.get_status("p", "u") is False


def test_get_project_retorna_copia_e_contagens(tmp_path: Path):
    cache = Cache(tmp_path / "cache.json")
    cache.set_status("p", "u1", True)
    cache.set_status("p", "u2", False)
    result = cache.get_project("p")
    result["u3"] = True
    assert cache.count("p") == 2
    assert cache.count_downloaded("p") == 1


def test_remove_existente_e_inexistente(tmp_path: Path):
    cache = Cache(tmp_path / "cache.json")
    cache.add("p", "u")
    assert cache.remove("p", "u") is True
    assert cache.remove("p", "u") is False


def test_clear_project_e_clear(tmp_path: Path):
    cache = Cache(tmp_path / "cache.json")
    cache.add("p1", "u1")
    cache.add("p2", "u2")
    cache.clear_project("p1")
    assert "p1" not in cache.data
    assert "p2" in cache.data
    cache.clear()
    assert cache.data == {}


def test_show_project_exibe_resumo(tmp_path: Path, capsys):
    cache = Cache(tmp_path / "cache.json")
    cache.add("p", "u")
    cache.show_project(" p ")
    out = capsys.readouterr().out
    assert "Projeto: p" in out
    assert "Total: 1" in out
    assert "Baixados: 1" in out
