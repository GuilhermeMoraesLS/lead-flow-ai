# Prompt mestre — organizar projeto que já possui PRD

Este projeto já possui um PRD. Sua tarefa é preparar o repositório para desenvolvimento assistido por agentes sem reescrever, substituir ou reinterpretar silenciosamente o PRD existente.

## Objetivo

Transformar o PRD existente em uma cadeia de contexto rastreável:

`PRD existente → auditoria de lacunas → SPEC técnica → slices verticais → harness`

Também devem ser preparados `AGENTS.md`, `RULES.md`, `CONTEXT.md`, `docs-agents/`, `.agents/harness/`, `.agents/skills/` e `.agents/skills-lock.json` quando ainda não existirem.

## Regras obrigatórias

1. Antes de editar, verifique a branch, `git status`, histórico recente e alterações locais. Preserve todo trabalho preexistente.
2. Localize o PRD informado pelo usuário. Se houver mais de um candidato, apresente os caminhos e solicite a escolha; não adivinhe.
3. Leia o PRD integralmente e registre sua revisão: caminho, commit mais recente quando versionado e hash do arquivo.
4. Trate o PRD como fonte primária de produto. Não mude requisitos, decisões, prioridades, escopo ou critérios para fazê-los combinar com o código atual.
5. Inspecione o repositório por buscas direcionadas. Não carregue todos os arquivos, dependências ou documentação indiscriminadamente.
6. Compare PRD e implementação atual e classifique cada ponto como:
   - já implementado e comprovado;
   - parcialmente implementado;
   - ainda não implementado;
   - divergente do comportamento atual;
   - ambíguo ou sem decisão;
   - não verificável no ambiente disponível.
7. Não presuma que um requisito está implementado porque existe código com nome semelhante. Exija evidência observável em código, teste ou execução.
8. Não presuma que o PRD está aprovado apenas porque existe. Procure estado, data, responsável ou evidência de aprovação. Caso não haja, marque como `[VALIDAÇÃO NECESSÁRIA]`.
9. Não implemente funcionalidades durante esta preparação.
10. Não crie nem modifique skills. Skills só podem ser baixadas de repositórios aprovados após auditoria e autorização explícita.

## Etapa 1 — auditoria do PRD

Produza `doc-specs/prd-audit.md` contendo:

- identificação e revisão do PRD;
- resumo do objetivo de negócio;
- atores e vocabulário;
- requisitos e critérios com seus IDs originais;
- requisitos sem ID, que devem receber IDs auxiliares apenas no relatório, sem editar o PRD;
- decisões pendentes e ambiguidades;
- contradições internas;
- elementos técnicos prematuros ou excessivamente prescritivos;
- matriz PRD × estado atual do produto;
- perguntas que realmente bloqueiam especificação ou implementação.

Não resolva sozinho decisões de negócio ausentes. Continue o trabalho independente e seguro; bloqueie somente o que depender delas.

## Etapa 2 — contexto progressivo

Crie ou adapte:

- `AGENTS.md`: entrada curta, regras universais e índice de leituras;
- `RULES.md`: autonomia, aprovações, proibições, evidências e precedência;
- `CONTEXT.md`: glossário, atores e invariantes extraídos do PRD;
- `docs-agents/architecture.md`: mapa observado do código;
- `docs-agents/validation.md`: comandos realmente existentes;
- `docs-agents/security.md`: dados, segredos e limites observados;
- `docs-agents/maintenance.md`: como manter o contexto sem duplicação.

Use `[A DEFINIR]` quando não houver evidência. Não invente uma arquitetura ideal.

## Etapa 3 — especificação técnica

Somente após separar as decisões pendentes, crie `doc-specs/SPEC-[slug].md`.

A SPEC deve:

- referenciar requisitos do PRD por IDs qualificados, por exemplo `PRD: RF-003`;
- separar requisitos, restrições, decisões e recomendações;
- mapear componentes e contratos afetados;
- definir dados, interfaces, autorização, erros e compatibilidade;
- tratar migração, concorrência, idempotência e recuperação somente quando pertinentes;
- definir estratégia de testes baseada em comportamento observável;
- registrar alternativas e decisões técnicas pendentes;
- possuir estado explícito: rascunho, validada ou bloqueada.

Não trate a criação da SPEC como aprovação.

## Etapa 4 — slices de implementação

Depois da aprovação necessária, crie `doc-specs/implementation-slices-[slug].md`.

Cada slice deve:

- entregar uma jornada vertical pequena e demonstrável;
- caber em uma sessão focada;
- declarar bloqueadores reais;
- referenciar IDs exatos do PRD e da SPEC;
- conter resultado esperado, escopo, fora de escopo, critérios `- [ ]`, testes e handoff;
- evitar divisões horizontais genéricas como “fazer backend”, “fazer frontend” e “fazer testes”;
- preservar compatibilidade e dados quando aplicável.

Se um slice não couber em uma sessão, subdivida por comportamento observável, não por camada.

## Etapa 5 — harness

Inicialize `.agents/harness/` com:

- `README.md` — ciclo de trabalho e critérios de estado;
- `state.json` — slices, dependências, Source IDs, critérios e evidências;
- `progress.md` — diário cronológico;
- `feedback.md` — problema → ação → verificação → estado;
- `handoff.md` — contexto mínimo para retomada;
- `impact-map.md` — requisito → slice → código → teste.

Estados permitidos: `planned`, `ready`, `in_progress`, `blocked`, `failed` e `done`.

`done` exige evidência de todos os critérios e revisão do diff. Documento existente, teste não executado ou relato humano sem comprovação não equivalem automaticamente a `done`.

## Etapa 6 — skills externas

Analise quais tarefas recorrentes realmente se beneficiariam de skills externas. Antes de baixar qualquer uma, apresente:

| Campo | Obrigatório |
| --- | --- |
| Nome e finalidade | Sim |
| Repositório e caminho | Sim |
| Mantenedor | Sim |
| Licença | Sim |
| Tag/commit fixo | Sim |
| Scripts ou executáveis | Sim |
| Permissões/efeitos esperados | Sim |
| Riscos e sobreposição | Sim |

Aguarde aprovação. Se aprovada, instale sem editar o conteúdo original e registre em `.agents/skills-lock.json`. Se não houver skill adequada, registre a lacuna; não crie uma.

## Ordem de execução e pausas

1. Faça a auditoria e o contexto progressivo.
2. Apresente decisões de produto que bloqueiam a SPEC.
3. Após resposta, produza ou finalize a SPEC.
4. Apresente decisões técnicas materiais.
5. Após resposta, produza os slices e inicialize o harness.
6. Proponha skills externas separadamente e aguarde aprovação antes do download.

## Entrega

Informe:

- arquivos criados ou alterados;
- revisão do PRD utilizada;
- divergências encontradas;
- decisões pendentes;
- estado da SPEC e dos slices;
- verificações realmente executadas;
- skills apenas propostas ou efetivamente instaladas;
- próximo passo mínimo recomendado.

