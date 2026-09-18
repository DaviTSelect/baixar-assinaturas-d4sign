from pathlib import Path

import pytest

import d4sign.config as config_module
from d4sign.config import Config, env_bool


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "sim", "on", "On"])
def test_env_bool_true(value):
    assert env_bool(value) is True


@pytest.mark.parametrize("value", ["0", "false", "no", "nao", "off", "qualquer"])
def test_env_bool_false(value):
    assert env_bool(value) is False


def test_config_load_carrega_e_converte_variaveis(monkeypatch):
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    values = {
        "D4SIGN_EMAIL": " user@example.com ",
        "D4SIGN_PASSWORD": "secret",
        "D4SIGN_BASE_URL": "https://example.test/",
        "D4SIGN_VAULT_ID": "42",
        "D4SIGN_VAULT_UUID": "vault-uuid",
        "DOWNLOAD_DIR": "saida",
        "CACHE_FILE": "dados/cache.json",
        "LOG_FILE": "logs/app.log",
        "HEADLESS": "sim",
        "PAGE_TIMEOUT": "11",
        "DOWNLOAD_TIMEOUT": "22",
        "DOWNLOAD_RETRIES": "4",
        "RETRY_DELAY": "0.5",
        "FOLDER_NAME_FILTER": "  contratos  ",
    }
    monkeypatch.setattr(config_module.os, "getenv", lambda key, default=None: values.get(key, default))

    cfg = Config.load()

    assert cfg.email == "user@example.com"
    assert cfg.password == "secret"
    assert cfg.base_url == "https://example.test"
    assert cfg.vault_id == "42"
    assert cfg.vault_uuid == "vault-uuid"
    assert cfg.download_dir == Path("saida")
    assert cfg.cache_file == Path("dados/cache.json")
    assert cfg.log_file == Path("logs/app.log")
    assert cfg.headless is True
    assert cfg.page_timeout == 11
    assert cfg.download_timeout == 22
    assert cfg.download_retries == 4
    assert cfg.retry_delay == 0.5
    assert cfg.folder_name_filter == "contratos"


def test_config_load_filtro_vazio_vira_none(monkeypatch):
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    monkeypatch.setenv("D4SIGN_EMAIL", "user@example.com")
    monkeypatch.setenv("D4SIGN_PASSWORD", "secret")
    monkeypatch.setenv("FOLDER_NAME_FILTER", "   ")
    cfg = Config.load()
    assert cfg.folder_name_filter is None


def test_config_load_rejeita_email_vazio(monkeypatch):
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    monkeypatch.setenv("D4SIGN_EMAIL", "")
    monkeypatch.setenv("D4SIGN_PASSWORD", "secret")
    with pytest.raises(RuntimeError, match="D4SIGN_EMAIL"):
        Config.load()


def test_config_load_rejeita_senha_vazia(monkeypatch):
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    monkeypatch.setenv("D4SIGN_EMAIL", "user@example.com")
    monkeypatch.setenv("D4SIGN_PASSWORD", "")
    with pytest.raises(RuntimeError, match="D4SIGN_PASSWORD"):
        Config.load()
