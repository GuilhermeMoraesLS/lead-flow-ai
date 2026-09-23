# Prompt — especificar uma funcionalidade

Crie ou atualize a documentação de `[FUNCIONALIDADE]` sem implementar código.

1. Leia `AGENTS.md`, `RULES.md`, `CONTEXT.md`, a constituição e apenas guias/código necessários.
2. Use skills externas instaladas somente quando a descrição corresponder à tarefa; não modifique nem crie skills.
3. Produza `doc-specs/PRD-[slug].md` com problema, usuários, regras, escopo, critérios Gherkin e decisões pendentes. Use IDs estáveis.
4. Pare para validar decisões de produto que alterem comportamento.
5. Após aprovação, produza `doc-specs/SPEC-[slug].md` com contratos, dados, segurança, compatibilidade, erros e testes, referenciando o PRD.
6. Pare para validar decisões técnicas materiais.
7. Após aprovação, produza `doc-specs/implementation-slices-[slug].md`: slices verticais, pequenos, dependências reais, Source IDs exatos, critérios `- [ ]`, verificação e handoff.
8. Atualize o harness com estado real. Criado ≠ aprovado ≠ implementado ≠ verificado.

