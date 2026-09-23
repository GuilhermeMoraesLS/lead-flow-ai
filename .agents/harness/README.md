# Harness de implementação

Memória operacional entre sessões; não substitui Git, PRD, SPEC ou testes.

## Início

1. Verifique branch, status e histórico recente.
2. Leia `state.json`, `progress.md`, `feedback.md` e `handoff.md`.
3. Escolha um slice autorizado, desbloqueado e incompleto.
4. Carregue regras, bloco do slice, Source IDs e handoffs diretos.
5. Inspecione apenas código/testes relacionados.

## Ciclo

**Observar → selecionar → agir → verificar → registrar.**

`done` exige todos os critérios comprovados. Use `blocked` para dependência externa e `failed` para verificação reprovada. Nunca transforme “não executado” em sucesso.

