from selenium.common.exceptions import WebDriverException

from d4sign.parser import DocumentParser

UUID = "12345678-1234-1234-1234-123456789abc"


class Element:
    def __init__(self, text="", attrs=None):
        self.text = text
        self.attrs = attrs or {}

    def get_attribute(self, name):
        return self.attrs.get(name)


class Row:
    def __init__(self, selectors=None, text="", outer_html=""):
        self.selectors = selectors or {}
        self.text = text
        self.outer_html = outer_html

    def find_elements(self, by, selector):
        value = self.selectors.get(selector, [])
        if isinstance(value, Exception):
            raise value
        return value

    def get_attribute(self, name):
        if name == "outerHTML":
            return self.outer_html
        return None


def test_uuid_encontra_em_atributo():
    row = Row({"input.chevmov": [Element(attrs={"value": UUID})]})
    assert DocumentParser.uuid(row) == UUID


def test_uuid_fallback_outerhtml():
    row = Row(
        {
            "input.chevmov": WebDriverException("falha"),
            "input[type='checkbox']": [],
            "[id^='nome_documento_']": [],
        },
        outer_html=f"<tr data-uuid='{UUID}'>",
    )
    assert DocumentParser.uuid(row) == UUID


def test_name_por_selector_e_fallback_texto():
    row = Row({"[id^='nome_documento_']": [Element(text=" Contrato ")]})
    assert DocumentParser.name(row) == "Contrato"

    fallback = Row(text="Finalizado\nDownload\nDocumento real")
    assert DocumentParser.name(fallback) == "Documento real"


def test_name_fallback_documento_quando_nao_acha():
    row = Row(text="Finalizado\nDownload")
    assert DocumentParser.name(row) == "documento"


def test_finalized_detecta_classe_e_comportamento_padrao():
    row = Row({".label-finalizado": [Element()]})
    assert DocumentParser.finalized(row) is True
    # A implementação atual considera True mesmo sem indicador.
    assert DocumentParser.finalized(Row()) is True


def test_download_element_escolhe_maior_pontuacao():
    comum = Element(text="Baixar PDF")
    melhor = Element(text="Download (apenas assinaturas)", attrs={"href": "/pdf"})
    row = Row({"a, button, input": [comum, melhor]})
    assert DocumentParser.download_element(row) is melhor


def test_download_element_retorna_none_em_erro():
    row = Row({"a, button, input": WebDriverException("falha")})
    assert DocumentParser.download_element(row) is None
