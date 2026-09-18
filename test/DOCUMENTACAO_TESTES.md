# Documentação de testes — projeto D4Sign

## 1. Escopo

A suíte foi criada para testar o comportamento das funções do projeto sem depender de uma sessão real da D4Sign. Foram identificados métodos de configuração, cache, parsing de DOM, controle de navegador, download, processamento, diagnóstico, modelos e orquestração principal.

Os testes usam `pytest`, `monkeypatch`, objetos fake e arquivos temporários. Isso permite validar a lógica em CI/CD, VPS ou máquina local sem abrir Chrome e sem realizar tráfego de produção.

## 2. Estratégia

### Testes unitários

Validam funções determinísticas e regras locais, por exemplo:

- extração e validação de UUID;
- sanitização de nomes;
- detecção de PDF por header;
- leitura e persistência do cache;
- parsing de elementos;
- construção de destinos;
- soma de estatísticas.

### Testes com mocks/fakes

Validam funções dependentes de browser/rede sem fazer chamadas reais:

- `D4SignBrowser.start()`;
- login e navegação;
- procura de pastas e documentos;
- sincronização de cookies;
- download HTTP;
- download Selenium;
- paginação e processamento;
- fechamento do navegador em caso de erro.

### Testes de filesystem

Usam `tmp_path` para criar PDFs, cache JSON, diagnósticos e diretórios de download de forma isolada.

## 3. Matriz de funções testadas

### `main.py`

| Função | Teste principal |
|---|---|
| `main()` | `test_main_orquestra_fluxo_e_fecha_browser`, `test_main_fecha_browser_mesmo_com_erro` |

### `d4sign/config.py`

| Função | Teste principal |
|---|---|
| `env_bool()` | `test_env_bool_true`, `test_env_bool_false` |
| `Config.load()` | `test_config_load_carrega_e_converte_variaveis`, testes de validação |

### `d4sign/models.py`

| Função/método | Teste principal |
|---|---|
| `Folder` | `test_modelos_folder_e_document` |
| `Document` | `test_modelos_folder_e_document` |
| `Statistics.add()` | `test_statistics_add_soma_campos_exceto_folders` |

### `d4sign/utils.py`

| Função | Teste principal |
|---|---|
| `extract_uuid()` | `test_extract_uuid` |
| `valid_uuid()` | `test_valid_uuid` |
| `sanitize_filename()` | testes `test_sanitize_filename_*` |
| `is_pdf()` | testes `test_is_pdf_*` |

### `d4sign/cache.py`

| Método | Teste principal |
|---|---|
| `Cache.__init__()` | `test_cache_init_sem_arquivo` |
| `load()` | `test_cache_load_normaliza_dados`, `test_cache_load_json_invalido_gera_cache_vazio` |
| `save()` | `test_cache_save_persiste_atomico` |
| `_project_key()` | `test_chaves_normalizadas` |
| `_uuid_key()` | `test_chaves_normalizadas` |
| `is_downloaded()` | `test_status_contains_get_status_e_add` |
| `contains()` | `test_status_contains_get_status_e_add` |
| `set_status()` | `test_set_status_uuid_vazio_nao_salva` e testes de status |
| `mark_downloaded()` | `test_mark_downloaded_e_mark_not_downloaded` |
| `mark_not_downloaded()` | `test_mark_downloaded_e_mark_not_downloaded` |
| `add()` | `test_status_contains_get_status_e_add` |
| `get_status()` | `test_status_contains_get_status_e_add` |
| `get_project()` | `test_get_project_retorna_copia_e_contagens` |
| `count()` | `test_get_project_retorna_copia_e_contagens` |
| `count_downloaded()` | `test_get_project_retorna_copia_e_contagens` |
| `remove()` | `test_remove_existente_e_inexistente` |
| `clear_project()` | `test_clear_project_e_clear` |
| `clear()` | `test_clear_project_e_clear` |
| `show_project()` | `test_show_project_exibe_resumo` |

### `d4sign/parser.py`

| Método | Teste principal |
|---|---|
| `DocumentParser.uuid()` | `test_uuid_encontra_em_atributo`, `test_uuid_fallback_outerhtml` |
| `DocumentParser.name()` | `test_name_por_selector_e_fallback_texto`, fallback padrão |
| `DocumentParser.finalized()` | `test_finalized_detecta_classe_e_comportamento_padrao` |
| `DocumentParser.download_element()` | `test_download_element_escolhe_maior_pontuacao`, teste de erro |

### `d4sign/debug.py`

| Método | Teste principal |
|---|---|
| `Debugger.__init__()` | `test_init_cria_diretorio` |
| `log()` | `test_log_separator_e_disabled` |
| `separator()` | `test_log_separator_e_disabled` |
| `page_info()` | `test_page_info` |
| `inspect_dom()` | `test_inspect_dom` |
| `save_state()` | `test_save_state_cria_arquivos` |
| `inspect_elements()` | `test_inspect_elements`, `test_inspect_elements_disabled` |
| `scroll_to()` | `test_scroll_to` |

### `d4sign/browser.py`

| Método | Teste principal |
|---|---|
| `D4SignBrowser.__init__()` | `test_init_e_current_driver` |
| `start()` | `test_start_configura_chrome` |
| `current_driver` | `test_init_e_current_driver` |
| `close()` | `test_close_fecha_e_limpa_driver` |
| `get()` | `test_get_abre_url_e_aguarda_dom`, teste de timeout |
| `login()` | `test_login_preenche_campos_e_clica` |
| `_find_login_button()` | `test_find_login_button_retorna_primeiro_visivel` |
| `_login_concluido()` | `test_login_concluido_por_url_indicador_e_erro` |
| `open_vault()` | `test_open_vault_monta_url` |
| `get_folders()` | `test_get_folders_extrai_nome_fallback_e_remove_duplicados` |
| `open_folder_page()` | `test_open_folder_page_retorna_rows` |
| `_save_diagnostic()` | `test_save_diagnostic_cria_png_e_html` |

### `d4sign/downloader.py`

| Método | Teste principal |
|---|---|
| `Downloader.__init__()` | `test_init_debug_flag_log_debug_exception_driver` |
| `_get_debug_flag()` | `test_get_debug_flag_booleano_e_fallback` |
| `log()` | `test_init_debug_flag_log_debug_exception_driver` |
| `debug()` | `test_init_debug_flag_log_debug_exception_driver` |
| `debug_exception()` | `test_init_debug_flag_log_debug_exception_driver` |
| `driver` | `test_init_debug_flag_log_debug_exception_driver` |
| `wait_document_ready()` | `test_wait_document_ready_complete` |
| `debug_page()` | `test_debug_page_executa_com_debug` |
| `scroll_page()` | `test_scroll_page_executa_scripts` |
| `find_document_rows()` | `test_find_document_rows_primeiro_selector_com_resultado` |
| `wait_for_documents()` | `test_wait_for_documents_retorna_quando_quantidade_estabiliza` |
| `sync_cookies()` | `test_sync_cookies_e_headers` |
| `_headers()` | `test_sync_cookies_e_headers` |
| `extract_download_url()` | testes `test_extract_download_url_*` |
| `find_download_button()` | `test_find_download_button_visivel` |
| `download_http()` | `test_download_http_pdf_valido`, teste de status/exceção |
| `list_files()` | `test_list_files_e_cleanup_temporary_files` |
| `cleanup_temporary_files()` | `test_list_files_e_cleanup_temporary_files` |
| `wait_for_download()` | `test_wait_for_download_detecta_pdf_estavel` |
| `download_selenium()` | `test_download_selenium_move_pdf_para_destino` |
| `download_document()` | `test_download_document_cache_http_e_fallback` |
| `build_destination()` | `test_build_destination_sanitiza_e_adiciona_pdf` |

### `d4sign/processor.py`

| Método | Teste principal |
|---|---|
| `Processor.__init__()` | `test_init_armazena_dependencias` |
| `process_specific_link()` | `test_process_specific_link_soma_todos_status`, erro de navegação |
| `process_document()` | testes `test_process_document_*` |
| `download_selenium()` | `test_download_selenium_processador` |

## 4. Resultado da execução

Comando de validação recomendado:

```bash
python -m pytest -c test/pytest.ini test --cov=d4sign --cov=main --cov-branch --cov-report=term-missing --cov-fail-under=100
```

No PowerShell/Windows:

```powershell
.\test\run_coverage.ps1
```

Resultado consolidado desta versão:

```text
176 passed
TOTAL: 1447 statements, 0 missing
BRANCHES: 374, 0 partial
COVER: 100%
```

Cobertura por módulo:

| Módulo | Linhas | Branches |
|---|---:|---:|
| `d4sign/browser.py` | 100% | 100% |
| `d4sign/cache.py` | 100% | 100% |
| `d4sign/config.py` | 100% | 100% |
| `d4sign/debug.py` | 100% | 100% |
| `d4sign/downloader.py` | 100% | 100% |
| `d4sign/models.py` | 100% | 100% |
| `d4sign/parser.py` | 100% | 100% |
| `d4sign/processor.py` | 100% | 100% |
| `d4sign/utils.py` | 100% | 100% |
| `main.py` | 100% | 100% |
| **Total** | **100%** | **100%** |

Os testes adicionais cobrem especialmente: exceções, timeouts, elemento ausente, clique normal/JavaScript, retries, cookies, HTML inesperado, HTTP não-PDF, arquivo temporário, PDF inválido, falhas de `unlink/replace/write`, arquivo desaparecendo durante a checagem e caminhos alternativos de loops/condições.

### Limite da métrica

100% de cobertura de linhas e branches significa que todo o código instrumentado e todos os lados das decisões reconhecidas pelo `coverage.py` foram executados. Isso é uma garantia forte contra código não exercitado, mas não prova literalmente todas as combinações possíveis de ambiente externo. Alterações reais da D4Sign, navegador, sistema operacional, rede e permissões precisam de testes de integração/E2E separados.

## 5. Observações encontradas durante a criação dos testes

### Dependências do projeto

O código importa:

- `requests`;
- `python-dotenv`;
- `webdriver-manager`;

mas essas bibliotecas não aparecem no `requirements.txt` original. Por isso elas foram incluídas em `test/requirements-test.txt` para que a suíte consiga coletar/importar o projeto corretamente.

### `DocumentParser.finalized()`

A implementação atual retorna `True` ao final mesmo quando nenhum seletor de “finalizado” é localizado. O teste registra exatamente esse comportamento atual. Se a regra de negócio exigir que somente documentos explicitamente finalizados sejam baixados, esse método merece revisão.

### `Statistics.add()`

O método soma `pages`, `documents`, `downloaded`, `cached`, `skipped` e `errors`, mas não soma `folders`. O teste preserva esse comportamento atual. Se `folders` também deveria ser agregado, a implementação deve ser ajustada posteriormente.

## 6. Testes reais de integração

A suíte entregue não autentica na D4Sign. Um teste de integração real seria separado dos unitários e precisaria de:

- credenciais de ambiente de teste;
- Chrome/Chromium disponível;
- rede liberada;
- um cofre controlado para testes;
- limpeza dos downloads gerados;
- execução manual ou pipeline protegido por secrets.

Isso evita que `pytest` comum cause downloads reais ou altere dados de produção.

## 7. Uso em CI/CD

Exemplo de etapa de validação:

```bash
python -m pip install -r test/requirements-test.txt
python -m pytest -c test/pytest.ini test --cov=d4sign --cov=main --cov-branch --cov-report=term-missing --cov-fail-under=100
```

A pipeline deve falhar automaticamente se qualquer teste falhar **ou se a cobertura cair abaixo de 100%**.
