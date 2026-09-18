# Testes automatizados

Esta pasta contém a suíte de testes automatizados do projeto D4Sign.

## Objetivo

Os testes validam todas as funções e métodos identificados em:

- `main.py`
- `d4sign/browser.py`
- `d4sign/cache.py`
- `d4sign/config.py`
- `d4sign/debug.py`
- `d4sign/downloader.py`
- `d4sign/models.py`
- `d4sign/parser.py`
- `d4sign/processor.py`
- `d4sign/utils.py`

A suíte é predominantemente **unitária**. Navegador, elementos Selenium, downloads HTTP e respostas externas são simulados com mocks/fakes para evitar login real, acesso à D4Sign e downloads de produção.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `conftest.py` | Configuração compartilhada e shims para ambientes sem Selenium |
| `test_utils.py` | UUID, sanitização de nomes e validação de PDF |
| `test_config.py` | Conversão de variáveis de ambiente e `Config.load()` |
| `test_models.py` | Dataclasses e soma de estatísticas |
| `test_cache.py` | Leitura, escrita, consulta e limpeza do cache |
| `test_parser.py` | Extração de UUID, nome, status e elemento de download |
| `test_debug.py` | Utilidades de diagnóstico e debug |
| `test_browser.py` | Inicialização, login, navegação, pastas e diagnóstico do browser |
| `test_downloader.py` | Localização de documentos, cookies, HTTP, Selenium e arquivos |
| `test_processor.py` | Paginação, processamento, cache, seleção por linha e download do `Processor` |
| `test_processor_duplicate_coverage.py` | Cache obsoleto, SHA-256, PDFs repetidos, auditoria final e ramos defensivos da correção antirrepetição |
| `test_edge_cases_100.py` | Exceções, timeouts, retries, filesystem, Selenium/HTTP e fallbacks para cobertura total de linhas |
| `test_branch_coverage_100.py` | Caminhos alternativos de `if/else`, loops e decisões para 100% de branch coverage |
| `test_main.py` | Orquestração completa de `main()` |
| `requirements-test.txt` | Dependências necessárias para os testes |
| `pytest.ini` | Configuração do pytest |
| `run_tests.sh` / `run_tests.ps1` | Atalhos Linux/Git Bash e PowerShell para executar a suíte |
| `run_coverage.sh` / `run_coverage.ps1` | Cobertura de linhas + branches com mínimo obrigatório de 100% |
| `DOCUMENTACAO_TESTES.md` | Documentação detalhada e matriz de cobertura funcional |

## Instalação

No diretório raiz do projeto:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r test/requirements-test.txt
```

O `requirements-test.txt` inclui também as dependências importadas pelo código durante a coleta dos testes (`selenium`, `webdriver-manager`, `requests` e `python-dotenv`).

## Executar todos os testes

```bash
pytest -q test
```

ou no Linux/Git Bash:

```bash
./test/run_tests.sh
```

ou no PowerShell:

```powershell
.\test\run_tests.ps1
```

Resultado validado na entrega:

```text
176 passed
```

## Executar com cobertura

```bash
python -m pytest -c test/pytest.ini test --cov=d4sign --cov=main --cov-branch --cov-report=term-missing --cov-fail-under=100
```

Linux/Git Bash:

```bash
./test/run_coverage.sh
```

PowerShell/Windows:

```powershell
.\test\run_coverage.ps1
```

Resultado validado nesta entrega:

- **100% de cobertura de linhas**: 1447/1447 statements;
- **100% de branch coverage**: 374/374 branches, 0 parciais;
- **176 testes passando**;
- `--cov-fail-under=100` faz a execução falhar se a cobertura cair abaixo de 100%.

## Executar apenas um módulo

```bash
pytest -q test/test_cache.py
pytest -q test/test_downloader.py
pytest -q test/test_processor.py
```

## Executar apenas um teste

```bash
pytest -q test/test_utils.py::test_is_pdf_valido
```

## Princípio de segurança dos testes

A suíte não deve utilizar credenciais reais, modificar o cache de produção nem acessar a D4Sign. Arquivos temporários são criados usando o fixture `tmp_path` do pytest e eliminados automaticamente pelo ambiente de teste.


## O que significa 100% aqui

A suíte executa todas as linhas mensuráveis e os dois lados de todas as decisões/branches instrumentadas pelo `coverage.py` no código atual. Isso inclui cenários de sucesso, ausência de elementos, timeout, retries, exceções do Selenium, respostas HTTP inválidas, falhas de filesystem, PDF inválido e fallbacks.

Mesmo 100% de line + branch coverage **não significa literalmente todas as situações possíveis do mundo real**. Combinações externas como mudanças futuras no HTML da D4Sign, versões de Chrome/driver, quedas de rede específicas, permissões do Windows/VPS e comportamento do servidor só podem ser cobertas por testes de integração/E2E controlados. A suíte unitária continua sem acessar produção.
