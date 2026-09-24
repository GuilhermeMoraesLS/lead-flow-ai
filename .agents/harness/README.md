# Harness — LeadFlow.IA v1

Memória operacional desta série de slices. Escopo: [plano de implementação](../../doc-specs/implementation-slices.md). Não representa autorização para executar todos os slices nem comprovação do produto.

## Autoridade e arquivos

[Regras atuais](../../RULES.md) → fontes PRD/SPEC → bloco autorizado → este registro. Divergência não se resolve sobrescrevendo a fonte: registrar o slice afetado como `blocked`, informar causa e aguardar decisão quando necessária.

| Arquivo | Uso |
| --- | --- |
| [state.json](state.json) | Estado de cada slice, origens separadas PRD/SPEC, dependências, liberação, próxima ação, revisões SHA-256 e evidência por critério de SL-00 |
| [impact-map.md](impact-map.md) | Localizar fonte → slice → contrato/artefato → evidência; distingue planejamento de execução |
| [progress.md](progress.md) | Histórico cronológico de alterações e verificações; acrescentar entradas, preservar anteriores |
| [feedback.md](feedback.md) | Somente falhas/bloqueios reais, com tratamento e situação |
| [handoff.md](handoff.md) | Estado atual, resultados, limitações e pacote da próxima sessão |

Os seis arquivos existentes foram usados; não há outro harness de feature criado nem alteração de skill.

## Retomada mínima

1. Conferir `git branch --show-current`, `git status --short`, `git log -1 --format='%H %s'` e diffs pertinentes. Preservar alterações preexistentes registradas.
2. Ler `state.json`, última entrada de progresso, feedback e handoff. Estados `planned` não autorizam execução.
3. Comparar hashes das fontes relevantes com `sourceRevisions`, usando `Get-FileHash -Algorithm SHA256 -LiteralPath <caminho>`. São hashes do conteúdo local, inclusive fontes ainda não commitadas.
4. Selecionar apenas slice autorizado, incompleto, com liberação confirmada e dependências concluídas. Se não houver, informar a próxima decisão necessária; não iniciar SL-01 por inferência.
5. Ler somente o bloco completo indicado em `sourcePath`, seus Source IDs nos arquivos correspondentes e handoffs das dependências diretas. Localizar trechos com `rg -n` e ler o intervalo pertinente.
6. Acrescentar apenas guias/código diretamente afetados. Iniciar com resultado e restrições; encerrar com critérios, evidências e próxima ação.

**Grafo de contexto:** PRD:ID → SPEC:ID → SL-xx → contrato/arquivo → evidência. As listas separadas preservam a origem; citar cenário PRD dentro da SPEC não muda seu namespace. Não carregar todos os 35 blocos para executar um slice.

## Revisões e invalidação

Mudança no PRD/SPEC: comparar IDs/trechos alterados, localizar relações em `impact-map.md` e `state.json`, revisar os slices consumidores e seus dependentes transitivos. Registrar a nova revisão somente após avaliar o impacto; evidência antiga não passa a cobrir nova fonte automaticamente. Mudança em RULES/guia operacional exige revalidar o procedimento aplicável. Mudança no plano exige conferir critérios/dependências do bloco afetado.

Se uma fonte contradiz o handoff ou há decisão bloqueante, marcar `blocked` com motivo e próxima ação; não fabricar uma solução. Registrar no progresso o alcance da revisão e manter evidências anteriores vinculadas à sua versão.

## Ciclo e estados

Observar → selecionar → agir → verificar → registrar.

- `planned`: previsto; autorização/prontidão ainda não comprovadas.
- `ready`: autorizado, dependências concluídas e decisões pertinentes resolvidas.
- `in_progress`: trabalho ou evidência ainda incompletos.
- `blocked`: dependência/decisão impede avanço.
- `failed`: verificação obrigatória reprovada.
- `done`: todos os critérios comprovados, verificações aplicáveis aprovadas e diff revisado.

Verificações têm estados independentes: `passed`, `failed`, `blocked`, `not_run`. Só `passed` comprova critério. As chaves locais `SL-00/AC1…AC4` e `EV-*` identificam critérios/evidências do harness; não são requisitos novos do PRD/SPEC.

O plano permanece como baseline de critérios abertos; resultados de execução ficam no harness, sem reescrever os requisitos. Nos próximos slices, registrar o texto exato dos critérios do bloco selecionado e suas evidências antes de considerar `done`.

## Verificação e encerramento

O harness começou como entrega documental e hoje também registra evidências locais dos SL-01–SL-09. A revisão D0 é somente documental: validar JSON, Source IDs, dependências, âncoras, hashes e diff, sem declarar bot, OpenAI ou testes de aplicação executados. [validation.md](../../docs-agents/validation.md) ainda não contém comandos de aplicação definidos; resultados de código anteriores estão registrados com seus procedimentos reais no `state.json`.

Para código futuro: confirmar seams com o usuário antes de escrever testes e seguir o ciclo aplicável do pedido/RULES. Guardar procedimento, esperado/observado, revisão e artefato, usando dados sintéticos e sem segredos. SL-10 é o próximo candidato de D0; `planned` e `nextCandidate` não constituem autorização para implementá-lo.

A política de modelo em RULES §12 está sem modelo preferido e com pausa HITL `NÃO`: atualizar com o modelo atual. Reconsultá-la a cada encerramento; nunca trocar modelo automaticamente. Em context rot, parar no estado verificável e produzir handoff parcial do mesmo slice.
