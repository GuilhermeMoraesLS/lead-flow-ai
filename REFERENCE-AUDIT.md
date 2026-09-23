# Auditoria da branch de referência

Referência: `glaucia86/codex-ai-pdlc-workshop`, branch `feat/implementacao-aprovacao-orcamento`, inspecionada em 2026-09-20.

## Estrutura observada

- `.agents/harness/`: README operacional, baseline, lista estruturada de funcionalidades, progresso, feedback, handoff, mapa de impacto e scripts de inicialização/verificação.
- `.agents/skills/`: skills de especificação, PRD, tickets, TDD, handoff, revisão, clean code e guias de frontend.
- `doc-specs/`: constituição, PRD, especificação, prompts e slices.
- `docs-agents/`: contexto, arquitetura, validação e manutenção.
- Raiz: `AGENTS.md`, `RULES.md` e `CONTEXT.md` como portas de entrada.

## O que vale generalizar

1. Divulgação progressiva reduz contexto irrelevante.
2. IDs ligando PRD → SPEC → slice → teste formam rastreabilidade útil.
3. Slices verticais limitam a sessão e produzem incrementos verificáveis.
4. Harness persistente evita depender do histórico de conversa.
5. Evidência precisa distinguir teste aprovado, falha, bloqueio e não execução.

## O que não deve ser copiado literalmente

- Regras específicas de Next.js/Nexo.
- Política ligada a um modelo específico.
- Dependência implícita de tracker/setup externo.
- Skills não auditadas ou não necessárias à stack do novo projeto.
- Estados, hashes, decisões e critérios do exemplo.

## Correção de nomenclatura

A pasta da branch é `doc-specs`, não `docs-specs`. Este template mantém o nome real para evitar links divergentes.

