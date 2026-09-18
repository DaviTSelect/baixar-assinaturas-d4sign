# Executar os testes

Execute os comandos na pasta do aplicativo, que contém `main.py` e `d4sign/`.

## Preparar o ambiente

Com Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r test/requirements-test.txt
.\.venv\Scripts\python.exe -m pytest test -q
```

Os exemplos seguintes consideram o ambiente virtual ativado:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Comandos úteis

```powershell
# Todos os testes
python -m pytest test -q

# Um módulo
python -m pytest test/test_cache.py -q

# Apenas os casos de expiração
python -m pytest test/test_cache.py -k expiration -q

# Relatório de cobertura de linhas e decisões
python -m pytest -c test/pytest.ini test --cov=d4sign --cov=main --cov-branch --cov-report=term-missing
```

Os scripts `run_tests.ps1` e `run_tests.sh` executam a suíte. Os scripts `run_coverage.ps1` e `run_coverage.sh` também exigem cobertura de 100% e falham abaixo desse limite. Essa exigência não significa que a versão atual atinja 100%.

O workflow de release executa `python -m pytest test -q`, sem exigir cobertura. Use o resultado da execução atual; números antigos de testes e cobertura não descrevem necessariamente o código atual.

## Como os testes funcionam

A suíte usa pytest, mocks, objetos simulados e `tmp_path`. A automação de navegador e as respostas de rede são simuladas. Os testes comuns não devem usar uma conta real do D4Sign.

[conftest.py](conftest.py) adiciona o projeto ao caminho de importação e fornece substitutos mínimos para Selenium e webdriver-manager quando não estão instalados. Isso não substitui as dependências necessárias para executar o aplicativo.

Alguns testes de Tkinter podem ser ignorados quando não há interface gráfica disponível. Confira o resumo do pytest e o motivo de cada teste ignorado.

Veja a [organização e os cenários de teste](DOCUMENTACAO_TESTES.md) e o [guia de desenvolvimento](../DESENVOLVIMENTO.md).
