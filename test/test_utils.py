from pathlib import Path

import pytest

from d4sign.utils import extract_uuid, is_pdf, sanitize_filename, valid_uuid

UUID = "12345678-1234-1234-1234-123456789abc"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        (f"prefixo/{UUID}/fim", UUID),
        ("sem uuid", None),
    ],
)
def test_extract_uuid(value, expected):
    assert extract_uuid(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (UUID, True),
        (f"  {UUID}  ", True),
        (None, False),
        ("abc", False),
        (f"x{UUID}", False),
    ],
)
def test_valid_uuid(value, expected):
    assert valid_uuid(value) is expected


def test_sanitize_filename_normaliza_nome():
    assert sanitize_filename('  contrato: teste / 2026?.pdf. ') == "contrato_ teste _ 2026_.pdf"


def test_sanitize_filename_fallback_e_limite():
    assert sanitize_filename("") == "SEM_NOME"
    assert sanitize_filename("   ...   ") == "SEM_NOME"
    assert len(sanitize_filename("a" * 300)) == 180


def test_is_pdf_valido(tmp_path: Path):
    pdf = tmp_path / "ok.pdf"
    pdf.write_bytes(b"%PDF-1.7\nconteudo")
    assert is_pdf(pdf) is True


def test_is_pdf_rejeita_inexistente_pequeno_e_header_invalido(tmp_path: Path):
    assert is_pdf(tmp_path / "nao-existe.pdf") is False

    pequeno = tmp_path / "pequeno.pdf"
    pequeno.write_bytes(b"1234")
    assert is_pdf(pequeno) is False

    invalido = tmp_path / "invalido.pdf"
    invalido.write_bytes(b"HELLO mundo")
    assert is_pdf(invalido) is False
