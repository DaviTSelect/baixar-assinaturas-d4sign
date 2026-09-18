# Organização dos testes

Para instalação e comandos, consulte o [README dos testes](README.md). Este guia mostra onde testar cada comportamento.

## Mapa da suíte

| Arquivo | Assunto |
|---|---|
| [test_config.py](test_config.py) | Ambiente, credenciais obrigatórias e conversão de configurações |
| [test_cache.py](test_cache.py) | JSON, status, persistência e expiração em 48 horas |
| [test_models.py](test_models.py) | Modelos e estatísticas |
| [test_utils.py](test_utils.py) | UUIDs, nomes de arquivos e cabeçalho PDF |
| [test_parser.py](test_parser.py) | Extração de informações da linha do documento |
| [test_browser.py](test_browser.py) | Chrome, login, navegação e diagnóstico |
| [test_sidebar.py](test_sidebar.py) | Menu lateral, links, hierarquia e expansão sob demanda |
| [test_desktop.py](test_desktop.py) | Interface, seleção, caminhos e sessão |
| [test_downloader.py](test_downloader.py) | Downloads HTTP e Selenium, temporários e falhas |
| [test_processor.py](test_processor.py) | Processamento e resultados por documento |
| [test_processor_duplicate_coverage.py](test_processor_duplicate_coverage.py) | Duplicatas, hash, cache inconsistente e auditoria |
| [test_debug.py](test_debug.py) | Diagnósticos |
| [test_updates.py](test_updates.py) | Versões, releases e integridade do instalador |
| [test_main.py](test_main.py) | Fluxo do terminal e encerramento do navegador |
| [test_edge_cases_100.py](test_edge_cases_100.py) | Exceções e caminhos alternativos |
| [test_branch_coverage_100.py](test_branch_coverage_100.py) | Decisões e ramos defensivos |

O sufixo `100` nos nomes é histórico. Ele não comprova cobertura total da versão atual.

## Cenários importantes

Ao mudar o cache, confira os instantes imediatamente antes, exatamente em e depois de 48 horas. Um JSON recente conserva os dados; um expirado é excluído e recriado vazio. Uma gravação recente reinicia o prazo. Os testes também devem verificar que uma segunda leitura não restaura dados expirados.

Ao mudar os downloads, cubra arquivo ausente, cabeçalho inválido, erro de download, repetição de conteúdo e reutilização de PDF existente. O seletor deve permanecer restrito à linha atual.

Ao mudar a árvore de pastas, confira nomes iguais, caracteres inválidos no Windows, seleção de pai e filho, expansão sob demanda e preservação do endereço da pasta.

Ao mudar a sessão, confira erro de login, fechamento, cancelamento e reutilização do navegador entre downloads. Ao mudar atualizações, confira versão inválida, instalador ausente, tamanho incorreto e SHA-256 divergente.

## Escrever novos testes

Use `tmp_path` para arquivos e `monkeypatch` para tempo, ambiente, navegador e rede. Evite esperas reais e dependência de arquivos pessoais. Teste o resultado esperado, incluindo erros relevantes para a alteração.

Os testes simulados não comprovam compatibilidade com o HTML atual do D4Sign. Um teste que passa com HTML antigo pode deixar de representar o site.

## Validação manual

Em uma conta de teste, confira:

1. Login e carregamento dos cofres.
2. Expansão de pastas e seleção com e sem subpastas.
3. Download de documentos com conteúdos diferentes e conferência dos arquivos.
4. Reexecução no mesmo destino, cancelamento e novo login.
5. Fechamento do Chrome ao sair.
6. Instalação e atualização entre versões, quando a mudança envolver distribuição.

Registre o comando executado, o resultado, os testes ignorados e as limitações. Gere um novo relatório antes de informar percentuais de cobertura.
