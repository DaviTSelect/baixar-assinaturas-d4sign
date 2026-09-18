# Orientações de manutenção

Este arquivo resume como trabalhar no projeto. O ponto de partida é o [guia de desenvolvimento](DESENVOLVIMENTO.md).

## Antes de alterar

- Confira `git status --short` para identificar alterações já existentes.
- Localize o módulo responsável pelo comportamento.
- Consulte os testes relacionados e mantenha desktop e terminal compatíveis quando usarem o mesmo módulo.

## Regras do projeto

- Busque o link de download dentro da linha do documento.
- Confirme o PDF no disco antes de aceitar o status do cache.
- Preserve a estrutura das pastas e o UUID no nome dos PDFs.
- Mantenha a expiração do JSON em 48 horas desde a última gravação.
- Use as filas da sessão para comunicar a automação com a interface.
- Use dados fictícios e diretórios temporários nos testes.
- Não inclua credenciais, PDFs reais, cache ou diagnósticos da conta no versionamento.

## Ao concluir

Execute os [testes relacionados](test/README.md), revise o diff e atualize a documentação se o comportamento mudou. Informe quais verificações foram executadas e suas limitações. Não declare cobertura total sem um relatório da versão testada.
