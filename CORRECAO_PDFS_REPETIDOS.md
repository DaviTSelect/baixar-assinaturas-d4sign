# Correção de PDFs repetidos no D4Sign

## Problema encontrado

O fluxo de `Processor.download_selenium()` abria o menu da linha atual, mas localizava o link de download com um XPath global (`//...`) na página. Isso permitia que o Selenium selecionasse repetidamente o primeiro link de download disponível, salvando o mesmo PDF com nomes/UUIDs diferentes.

Além disso, o cache era consultado antes de validar o arquivo no disco. Assim, um UUID marcado como baixado podia ser pulado mesmo quando o PDF estivesse ausente, inválido ou fosse uma cópia de outro documento.

## Correções aplicadas

1. O link de download agora é localizado exclusivamente dentro da linha (`row`) que está sendo processada por meio de `DocumentParser.download_element(row)`.
2. O disco passou a ser a fonte de verdade: cache só é aceito quando o PDF correspondente existe e é válido.
3. Cache obsoleto é invalidado e o UUID volta a ser baixado.
4. PDFs são comparados por conteúdo usando SHA-256, com índice por tamanho para evitar hash desnecessário em milhares de arquivos.
5. Um PDF baixado que seja idêntico a outro UUID é rejeitado e não é aceito como sucesso.
6. PDFs repetidos deixados por execuções antigas são detectados quando o UUID é processado e são baixados novamente.
7. Ao final, uma auditoria confirma quantos UUIDs esperados possuem PDF válido e único e lista qualquer pendência.
8. A lógica respeita `download_retries` da configuração em vez de fixar sempre três tentativas.

## Garantia operacional

O programa não marca um novo UUID como baixado se o arquivo final não for um PDF válido. Também não aceita silenciosamente um PDF cujo conteúdo SHA-256 seja igual ao de outro UUID da mesma pasta.

A auditoria final informa explicitamente se todos os documentos encontrados terminaram com arquivos válidos e únicos. Falhas externas permanentes (site fora do ar, sessão expirada, bloqueio do navegador, falta de permissão ou rede indisponível) ainda podem impedir um download; nesses casos o UUID permanece pendente e a auditoria não declara conclusão total.

## Testes

A suíte atual valida a correção com cobertura obrigatória de linhas e branches:

- 176 testes;
- 176 passando;
- 1447 statements cobertos;
- 374 branches cobertos;
- 100% line coverage;
- 100% branch coverage.

No PowerShell:

```powershell
.\test\run_coverage.ps1
```
