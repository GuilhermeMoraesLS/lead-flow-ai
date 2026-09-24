Implemente exclusivamente o slice `[SXX]` em doc-specs\implementation-slices.md

Use `RULES.md` como roteador. Leia apenas o estado, handoff, bloco do slice, Source IDs, código e testes diretamente relacionados.

Implemente e valide conforme o projeto. Depois atualize:

- `state.json`;
- uma entrada curta em `progress.md`;
- `handoff.md`;
- `feedback.md` somente se houver falha ou bloqueio;
- `impact-map.md` somente se a rastreabilidade mudar.

Marque `done` somente com todos os critérios comprovados. Não avance para outro slice.



----


Implemente exclusivamente o primeiro slice de  de `[doc-specs/implementation-slices.md]`

Siga `RULES.md` como contrato e roteador de contexto. Não carregue toda a documentação por padrão.

## Preparação

1. Verifique branch, `git status`, alterações locais e o harness da feature.
2. Confirme que o slice está autorizado, `ready` e com bloqueadores concluídos.
3. Carregue apenas:
   - bloco completo do slice;
   - Source IDs correspondentes no PRD e na SPEC;
   - handoffs das dependências diretas;
   - guias, código, testes e skills externas diretamente aplicáveis.
4. Se uma fonte divergir do handoff ou houver decisão bloqueante, registre `blocked` e não invente uma solução.

Antes de editar, informe brevemente: resultado esperado, critérios, impacto provável, fora de escopo e verificações planejadas.

## Implementação

- Trabalhe em ciclos Red → Green → Refactor quando aplicável.
- Implemente a menor jornada vertical que cumpra o slice.
- Preserve comportamento e trabalho fora do escopo.
- Não antecipe slices, instale dependências/skills ou faça mudança arquitetural sem aprovação.
- Use dados isolados e respeite as regras de segurança e autorização do projeto.

## Validação

1. Execute testes focados e depois as verificações obrigatórias de `docs-agents/validation.md`.
2. Revise o diff e arquivos não rastreados.
3. Relacione cada Acceptance Criterion à evidência observada.
4. Marque `[x]` somente quando o critério estiver implementado e comprovado; mantenha `[ ]` diante de falha, bloqueio ou verificação pendente.
5. Diferencie `passed`, `failed`, `blocked` e `not_run`; somente `passed` comprova o critério.

Se surgirem sinais de context rot — repetição, contradição, esquecimento ou contexto excessivo — pare em estado verificável, atualize um handoff parcial e recomende retomar o mesmo slice em sessão nova.

## Encerramento

Consulte em `RULES.md` a política de modelo/HITL. Nunca troque o modelo automaticamente. Se houver pausa obrigatória antes de atualizar o harness, apresente o estado real e aguarde autorização.

Quando autorizado, atualize o harness da feature:

- `state.json`: status e evidências por critério;
- `progress.md`: alterações, decisões e verificações;
- `feedback.md`: apenas falhas ou bloqueios reais;
- `handoff.md`: estado, evidências, pendências e próxima ação;
- `impact-map.md`: somente se a rastreabilidade mudou.

Use `done` apenas quando todos os critérios estiverem comprovados, as verificações obrigatórias aprovadas e o diff revisado. Caso contrário, use `in_progress`, `blocked` ou `failed`.

Na resposta final, informe resultado, arquivos, testes, critérios comprovados/pendentes, status do harness e próximo passo. Não inicie outro slice.

