# Agentic Project Bootstrap

Template independente de stack para iniciar projetos com contexto progressivo, especificações rastreáveis, skills externas auditáveis e memória operacional para agentes de código.

## Estrutura gerada

```text
AGENTS.md
RULES.md
CONTEXT.md
.agents/
  harness/
  skills/          # somente skills instaladas de repositórios
  skills-lock.json
doc-specs/
docs-agents/
prompts/
```

## Sequência

1. Em projeto novo, execute `prompts/00-bootstrap.md`. Se já houver PRD, use `prompts/00b-existing-prd.md`.
2. Revise os itens `[A DEFINIR]` e a lista proposta de skills externas.
3. Autorize explicitamente as skills que podem ser baixadas.
4. Execute `prompts/01-specify-feature.md` para cada iniciativa.
5. Execute `prompts/02-implement-slice.md` para um slice por vez.
6. Use `prompts/03-resume.md` em uma nova sessão.

O agente não cria skills. Ele pode pesquisar, comparar e propor skills existentes; instalação exige origem, revisão fixa, licença e aprovação.

## Função das pastas

- `doc-specs`: por que/o que construir, contratos e slices.
- `docs-agents`: mapa técnico carregado sob demanda.
- `.agents/skills`: capacidades externas instaladas e fixadas.
- `.agents/harness`: estado vivo da implementação; não substitui Git, requisitos ou testes.
