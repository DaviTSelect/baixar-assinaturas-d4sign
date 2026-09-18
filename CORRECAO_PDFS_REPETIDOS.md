# Verificação de PDFs repetidos

## Problema que motivou a regra

Um seletor global de download podia retornar o link de outro documento. O mesmo PDF acabava salvo com nomes e UUIDs diferentes. O cache também podia indicar sucesso para um arquivo ausente ou incorreto.

## Funcionamento atual

O fluxo de [Processor](d4sign/processor.py) segue estas etapas:

1. Obtém o UUID e monta o destino `Nome - UUID.pdf`.
2. Verifica o arquivo existente com `is_pdf()`.
3. Compara possíveis duplicatas da mesma pasta por tamanho e SHA-256.
4. Se o PDF estiver ausente, inválido ou repetido, invalida o status no cache e tenta baixar novamente.
5. Localiza o botão com `DocumentParser.download_element(row)`, dentro da linha atual.
6. Valida o download antes de marcar sucesso no cache.
7. Audita os arquivos esperados ao terminar a localização.

O número de tentativas vem de `download_retries`. Um PDF existente, válido e sem duplicata pode ser reutilizado mesmo após a renovação do JSON.

## Limites da verificação

`is_pdf()` confere a existência, o tamanho mínimo e o cabeçalho `%PDF-`. Não analisa todas as páginas nem valida assinaturas digitais.

A comparação de conteúdo ocorre na mesma pasta de destino. Dois documentos distintos com bytes idênticos são tratados como duplicados pela regra atual. A auditoria abrange os documentos encontrados durante o processamento, não comprova que o site exibiu todos os documentos da conta.

O resultado fica em `Processor.last_audit`:

| Campo | Significado |
|---|---|
| `expected` | Quantidade de documentos esperados |
| `valid_unique` | Quantidade de arquivos válidos sem duplicata identificada |
| `missing` | UUIDs com arquivo ausente ou inválido |
| `duplicate_uuids` | UUIDs envolvidos em duplicidade |
| `duplicate_pairs` | Pares identificados como repetidos |
| `complete` | Indica ausência de pendências na auditoria |

## Testar uma alteração

Na pasta do aplicativo, com as dependências de teste instaladas:

```powershell
python -m pytest test/test_processor.py test/test_processor_duplicate_coverage.py test/test_parser.py -q
```

Veja [como preparar os testes](test/README.md). Alterações nos seletores também devem ser verificadas manualmente com documentos de conteúdos diferentes.
