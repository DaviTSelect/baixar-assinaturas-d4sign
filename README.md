# D4Sign Central Bolsas — Desktop

Aplicativo para Windows x64 que baixa documentos do D4Sign usando o Chrome oculto. Depois do login, carrega os cofres e a árvore de pastas da conta para seleção por nome. Possui acompanhamento da execução e atualização pelo último release estável do GitHub. A execução original por terminal continua disponível em `main.py`.

## Para os colaboradores

1. Instale o Google Chrome e mantenha acesso à internet e à sua conta D4Sign.
2. Baixe `D4Sign-Setup-VERSAO.exe` na [página de releases](https://github.com/DaviTSelect/baixar-d4sign-centralbolsas/releases/latest), depois que a primeira versão for publicada.
3. Execute o instalador e abra **D4Sign Central Bolsas** pelo atalho.
4. Informe seu e-mail e senha e clique em **Entrar**. O aplicativo lê os cofres e pastas já presentes no menu lateral, sem abrir cada cofre nem suas páginas de documentos. Não é necessário informar links, IDs ou UUIDs.
5. Expanda a árvore para carregar as subpastas sob demanda, usando os controles do menu do próprio site em segundo plano. Selecione pelo nome; use Ctrl para selecionar vários itens. **Incluir todas as subpastas** vem marcado; desmarque para baixar apenas documentos diretamente nos itens selecionados. Ao baixar com essa opção marcada, somente os ramos selecionados são expandidos automaticamente.
6. Escolha a pasta de destino e clique em **Baixar selecionados**, ou use **Baixar tudo da conta** para incluir todos os cofres e suas subpastas.
7. Aguarde a conclusão. Use **Atualizar lista** para recarregar a estrutura ou **Sair da conta** para encerrar a sessão. O navegador permanece oculto até o logout ou fechamento do aplicativo.

Antes de cada download, o aplicativo mostra uma confirmação com os links de origem no D4Sign e os caminhos locais de destino. Escolha **Sim** para iniciar ou **Não** para cancelar sem baixar. Em erro, logout, atualização ou fechamento da janela, a sessão encerra o Chrome utilizado pela automação.

Durante um download, **Cancelar download** encerra o Chrome da automação, interrompe a operação e finaliza a sessão. Será necessário entrar novamente para iniciar outro download. Arquivos incompletos não são mantidos pelo downloader.

Exemplo: ao escolher a subpasta `Financeiro / Contratos / 2026`, os PDFs serão salvos em `DESTINO/Financeiro/Contratos/2026`. Pastas vazias também são criadas. Caracteres proibidos pelo Windows são substituídos; nomes que colidem recebem um sufixo numérico. A seleção de um cofre e de uma de suas pastas não repete o processamento da pasta. Os PDFs mantêm o nome do documento com seu identificador interno como sufixo para evitar colisões.

Python não precisa ser instalado na máquina dos colaboradores. Na primeira execução, o gerenciador de drivers baixa o ChromeDriver compatível; a rede da empresa precisa permitir esse download. Contas com CAPTCHA ou autenticação adicional ainda não têm fluxo interativo implementado; o aplicativo informa a falha de login.

A descoberta usa os itens `liCofre_...` e `liFolder_...` do menu autenticado, seus nomes e links completos, sem exigir tokens da API. Os identificadores numéricos do menu não são confundidos com os identificadores dos documentos. Links de pastas preservam o caminho `/desk/cofres/ID/COFRE/PASTA.html`; só são abertos para baixar documentos. Os testes incluem o HTML fornecido da conta (cofre Recursos Humanos e pasta Aditivo), carregamento sob demanda e associação de itens irmãos do menu. A expansão por AJAX e o download ainda precisam de validação na sessão real.

O desktop consulta documentos sem o filtro fixo de finalizados da versão VPS. Apenas os documentos que o site permite baixar como PDF serão concluídos; itens sem download disponível aparecem como erros. O mecanismo de download e a auditoria de PDFs existentes foram preservados.

As credenciais são usadas somente durante a execução e não são salvas. Diagnósticos ficam em `%LOCALAPPDATA%\D4SignDesktop`. Downloads e cache ficam fora da instalação e são preservados nas atualizações e desinstalações. Evite executar duas instâncias sobre a mesma pasta de destino.

## Atualizações

O aplicativo consulta atualizações antes de permitir o login e pelo botão **Verificar atualização**. A consulta usa o repositório definido em `d4sign/version.py`. Quando houver uma versão estável superior, o aplicativo baixa automaticamente o instalador, verifica tamanho e SHA-256, encerra o Chrome/sessão quando necessário, fecha a versão atual e abre o instalador. Não é possível instalar durante um processamento. Falhas de rede não impedem o uso da automação; nesse caso, a versão atual continua disponível.

São aceitos releases estáveis com tags `vMAJOR.MINOR.PATCH` e o asset exato `D4Sign-Setup-MAJOR.MINOR.PATCH.exe`, com digest SHA-256 fornecido pelo GitHub. Releases sem instalador ou digest não são instalados. A comparação usa a API de [último release do GitHub](https://docs.github.com/en/rest/releases/releases#get-the-latest-release), que exclui rascunhos e pré-releases.

O atualizador funciona com releases acessíveis publicamente, sem token embutido. Para repositório privado, use um repositório público separado apenas para distribuir os instaladores e ajuste `REPOSITORY`, ou implemente autenticação individual antes da distribuição. O instalador ainda não tem assinatura digital de código.

O `.gitignore` cobre `.env`, credenciais, cache, logs, PDFs, downloads, diagnósticos, builds, instaladores gerados e arquivos compactados locais. Antes de enviar ao GitHub, confira `git status --ignored` e use `git status --short` para revisar somente os arquivos que serão versionados. Se algum segredo já tiver sido commitado anteriormente, removê-lo do `.gitignore` não apaga o histórico; revogue a credencial e reescreva o histórico conforme a política do repositório.

## Desenvolvimento

No Windows, com Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python desktop.py
```

Para continuar usando a VPS, configure `D4SIGN_EMAIL` e `D4SIGN_PASSWORD` no ambiente ou em `.env` e execute `python main.py`. As credenciais antigas embutidas foram removidas.

## Gerar e publicar uma versão

Na máquina de desenvolvimento, instale [Inno Setup 6](https://jrsoftware.org/isinfo.php). O build usa [PyInstaller](https://pyinstaller.org/en/stable/usage.html) e deve ser feito no Windows x64:

```powershell
python -m pip install -r requirements-build.txt pytest
python -m pytest test -q
.\scripts\build.ps1
```

O instalador ficará em `dist/installer/D4Sign-Setup-VERSAO.exe`. Para gerar somente a pasta executável, use `./scripts/build.ps1 -ExecutableOnly` e distribua **toda** a pasta `dist/D4Sign`, não apenas o `.exe`.

Para publicar pelo GitHub Actions:

1. Atualize `VERSION` em `d4sign/version.py` e envie as alterações ao repositório.
2. Crie e envie a tag correspondente, por exemplo `v1.0.0`.
3. O workflow `.github/workflows/release.yml` executa os testes, gera o instalador e cria um release em **rascunho**. A tag precisa coincidir com `VERSION`.
4. Baixe o instalador do rascunho e valide instalação, login, downloads e atualização em uma máquina Windows de teste.
5. Publique o release estável; só então ele será oferecido aos colaboradores.

O workflow também pode ser executado manualmente para gerar um artefato sem publicar release. A atualização deve ser validada entre duas versões reais publicadas; os testes automatizados usam respostas e downloads simulados e não acessam a conta D4Sign.
