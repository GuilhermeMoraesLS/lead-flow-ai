# Contrato operacional para agentes

## Antes de agir

1. Leia `AGENTS.md` e as fontes indicadas para a tarefa.
2. Verifique branch, status e alterações locais.
3. Identifique resultado, fora de escopo, critérios, impacto e validações.
4. Para implementação, confirme que PRD, SPEC e slice estão aprovados.

## Autonomia

Um pedido de implementação autoriza inspecionar, editar, testar e documentar o necessário ao resultado aprovado. Diagnóstico ou planejamento isolado não autoriza implementar. Mudanças adicionais de produto, infraestrutura ou processo exigem decisão.

## Aprovação obrigatória

Pare antes de ação ainda não autorizada que envolva decisão de produto, contrato incompatível, migração ou perda de dados, dependência, skill externa, infraestrutura, custo, publicação, deploy, merge, mensagem externa, descarte de alterações ou operação destrutiva.

Para baixar uma skill, apresente repositório, caminho, finalidade, revisão/commit, licença, arquivos/scripts executáveis, permissões esperadas e riscos. Aguarde aprovação explícita.

## Proibições

- Não contornar permissões ou revelar segredos.
- Não fabricar testes, status, commits ou aprovações.
- Não apagar/enfraquecer testes para obter sucesso artificial.
- Não alterar requisitos para justificar código.
- Não usar dados reais como massa de teste.
- Não criar, completar ou modificar o conteúdo de uma skill. Atualizações vêm de sua origem aprovada.

## Evidência e conclusão

- Teste comportamento observável, recusas, limites e regressões relevantes.
- Use dados isolados e registre procedimento, resultado, revisão e pendências.
- Não executado, bloqueado e reprovado são estados distintos.
- Só marque conclusão quando critérios têm evidência, o diff foi revisado e o harness reflete o estado real.

## Precedência

1. Plataforma e permissões.
2. Pedido atual do usuário.
3. `AGENTS.md` e `RULES.md`.
4. PRD/SPEC aprovados.
5. Slice autorizado.
6. Guias, skills aprovadas e harness.
7. Convenções inferidas do código.

