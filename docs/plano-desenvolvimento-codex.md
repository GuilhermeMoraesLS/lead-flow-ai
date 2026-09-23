# LeadFlow.IA — Plano de Desenvolvimento para Claude Code

Este documento organiza o projeto em fases modulares e define a estrutura de contexto (CLAUDE.md, docs, skills, subagents, prompts) para que o Claude Code desenvolva com o mínimo de erro e retrabalho.

**Fonte de verdade:** o Pré-PRD (documento de escopo) prevalece sobre o PRD original onde há conflito. As diferenças que importam já estão consolidadas na seção 1.

---

## 1. Decisões consolidadas (o que o Claude Code precisa saber antes de escrever uma linha)

| Tema | Decisão | Origem |
|---|---|---|
| Nome do produto | LeadFlow.IA | conversa |
| Canal do MVP | Telegram (garantido) → WhatsApp não-oficial (Evolution API) → Voz Twilio (condicional) → WhatsApp oficial (futuro) | Pré-PRD |
| Arquitetura | AI Core agnóstico de canal + adaptadores por canal, contrato comum de entrada/saída | Pré-PRD §3 |
| Orquestração do agente | LangGraph (Python), em código — sem n8n | conversa |
| Fluxos temporizados (follow-up) | Fila de tarefas: Celery + Redis; regras fixas de tempo, IA só escreve o texto | conversa |
| Bot Telegram | Um bot por cliente; criado via BotFather por conta mestre; nome e foto via `setMyName` / `setMyProfilePhoto` | conversa |
| Onboarding | Self-service, sem demo; cliente configura tudo no web app | conversa |
| Multi-tenancy | `organization_id` em tudo + Row Level Security no Supabase | PRD §14 |
| LLM | Abstraído por `LLMProvider` (OpenAI no PRD, mas trocável) | PRD §16 + recomendação |
| Stack | Backend Python/FastAPI · Frontend Next.js · Supabase/Postgres + pgvector · Supabase Auth | PRD §16 |
| Fora do MVP | CRM externo, multi-idioma, billing, app nativo, múltiplos agentes por empresa, Instagram/Ads | Pré-PRD §5 |

**Decisões a travar antes da Fase 0** (o Claude Code não deve decidir sozinho):
1. **Monorepo ou dois repos?** → Recomendo monorepo (`apps/api`, `apps/web`, `packages/`) — o Claude Code enxerga o contrato Core↔Adapter e o frontend no mesmo contexto.
2. **Supabase hosted ou local?** → Hosted para o projeto (o conector Supabase MCP já está ligado na sua conta), com `supabase start` local para testes.
3. **Deploy:** Railway ou Render para API + worker; Vercel para o Next.js. Não precisa decidir agora, mas o `docker-compose` da Fase 0 já deve deixar isso trivial.
4. **LLM padrão do MVP:** OpenAI (como no PRD) ou Anthropic. Qualquer um serve — o importante é o `LLMProvider` desde o primeiro commit.

---

## 2. Estrutura do repositório

```
leadflow/
├── CLAUDE.md                     ← regras do projeto (seção 3)
├── docs/
│   ├── 00-pre-prd.md             ← o documento de escopo, na íntegra
│   ├── 01-prd.md                 ← PRD original (referência)
│   ├── 02-decisions.md           ← tabela da seção 1 + ADRs curtos
│   ├── 03-contracts.md           ← contrato Core↔Adapter (Fase 0)
│   ├── 04-data-model.md          ← schema + RLS (Fase 1)
│   └── phases/
│       ├── phase-0.md … phase-8.md  ← um arquivo por fase (seção 4)
├── .claude/
│   ├── skills/                   ← skills do projeto (seção 5)
│   ├── agents/                   ← subagents (seção 6)
│   └── settings.json             ← hooks (seção 6)
├── apps/
│   ├── api/                      ← FastAPI + LangGraph + Celery
│   │   ├── src/leadflow/
│   │   │   ├── core/             ← AI Core (NUNCA importa de channels/)
│   │   │   ├── channels/         ← adapters: telegram/, evolution/, voice/, console/
│   │   │   ├── contracts/        ← InboundMessage, OutboundMessage, ChannelAdapter, LLMProvider
│   │   │   ├── db/               ← repositórios, migrations
│   │   │   ├── tasks/            ← Celery: follow-ups, timeouts
│   │   │   └── api/              ← rotas FastAPI
│   │   └── tests/
│   │       ├── unit/
│   │       ├── contracts/        ← testes que todo adapter precisa passar
│   │       └── golden/           ← conversas de referência do agente
│   └── web/                      ← Next.js
├── supabase/
│   └── migrations/
├── docker-compose.yml            ← postgres (ou supabase local), redis, api, worker
└── Makefile                      ← make dev / test / lint / migrate
```

A regra que evita a maior parte do retrabalho: **`core/` não conhece `channels/`**. Se o Claude Code tentar importar um adapter dentro do core, um teste de arquitetura (`tests/unit/test_architecture.py` com `import-linter`) falha.

---

## 3. CLAUDE.md (cole na raiz do repo)

```markdown
# LeadFlow.IA

Agente de IA (SDR) que atende, qualifica e encaminha leads. Um único AI Core
agnóstico de canal + adaptadores por canal. Multi-tenant por organization_id.

## Leia antes de qualquer tarefa
- docs/00-pre-prd.md — escopo e prioridades (fonte de verdade)
- docs/02-decisions.md — decisões travadas; não reabra sem perguntar
- docs/03-contracts.md — contrato Core↔Adapter e LLMProvider
- docs/phases/phase-N.md — a fase atual, com Definition of Done

## Stack
Python 3.12 / FastAPI / LangGraph / Celery+Redis / Supabase (Postgres + pgvector + Auth) / Next.js 15 / TypeScript

## Regras de arquitetura (invioláveis)
1. `core/` NUNCA importa de `channels/`. Adapters implementam `ChannelAdapter`.
2. Toda query ao banco filtra por `organization_id`. RLS está ligado; nunca use service_role no caminho do usuário.
3. LLM só via `LLMProvider`. Nenhuma chamada direta a SDK de LLM fora de `core/llm/`.
4. O agente NÃO inventa informação comercial: só responde preço/produto/política a partir do que veio de tools (KB, products). Sem fonte → escala para humano.
5. Follow-ups são agendados por regra (Celery), nunca por `sleep`/loop. A IA só gera o texto.
6. Nada de conhecimento de empresa hardcoded. Tudo vem da configuração da organização.

## Como trabalhar
- Antes de codar: leia a fase atual, liste os arquivos que vai tocar, e proponha o plano em 5–10 linhas. Espere aprovação se a fase disser "plan first".
- Diffs pequenos. Um commit por unidade coerente. Mensagem: `feat(core): …`, `fix(telegram): …`, `test(golden): …`.
- Escreva ou atualize testes junto com o código. `make test` e `make lint` devem passar antes de dizer "pronto".
- Se precisar tomar uma decisão que não está em docs/02-decisions.md, pergunte e depois registre lá.
- Ao terminar a fase, atualize docs/phases/phase-N.md com o que foi feito e o que ficou pendente.

## Comandos
make dev        # sobe postgres, redis, api, worker, web
make test       # pytest apps/api + vitest apps/web
make lint       # ruff + mypy + eslint
make migrate    # aplica migrations supabase
make golden     # roda só os testes de conversa do agente

## Não faça
- Não instale libs novas sem justificar em uma linha no PR/commit.
- Não crie um segundo caminho de acesso ao LLM ou ao banco "só para testar".
- Não mexa em migrations já aplicadas; crie uma nova.
- Não altere o contrato em docs/03-contracts.md sem uma ADR.
```

---

## 4. Fases de desenvolvimento

Cada fase tem: objetivo, contexto a carregar, entregáveis, Definition of Done e o prompt de kickoff para colar no Claude Code. Trabalhe **uma fase por sessão**; use `/clear` entre fases para manter o contexto limpo.

### Fase 0 — Fundação e contratos

**Objetivo:** repositório funcionando com tooling, e o contrato Core↔Adapter definido e testado antes de existir qualquer canal. É a fase que mais evita retrabalho.

**Contexto:** `CLAUDE.md`, `docs/00-pre-prd.md` (§3 e §6), `docs/02-decisions.md`.

**Entregáveis:**
- Estrutura do monorepo, `Makefile`, `docker-compose.yml`, `pyproject.toml` (uv ou poetry, ruff, mypy, pytest), Next.js inicializado.
- `contracts/`: `InboundMessage`, `OutboundMessage`, `ChannelAdapter` (Protocol/ABC), `LLMProvider` (Protocol), `AgentCore.handle(inbound) -> list[OutboundMessage]`.
- `docs/03-contracts.md` documentando cada campo (org_id, channel, external_chat_id, external_user_id, text, media, metadata, timestamp).
- `tests/contracts/test_channel_adapter.py`: suíte parametrizada que qualquer adapter precisa passar.
- `channels/console/` — adapter de terminal (stdin/stdout) que já passa na suíte. É o primeiro "canal" e o que vai permitir testar o Core sem Telegram.
- `tests/unit/test_architecture.py` com import-linter (core não importa channels).
- CI mínimo (GitHub Actions: lint + test).

**DoD:** `make dev` sobe tudo; `make test` verde; console adapter conversa com um `EchoCore` de mentira.

**Prompt de kickoff:**
```
Estamos iniciando o LeadFlow.IA. Leia CLAUDE.md, docs/00-pre-prd.md (seções 3 e 6)
e docs/02-decisions.md. Esta é a Fase 0: fundação e contratos.

Antes de codar, proponha em até 10 linhas: estrutura de pastas, ferramentas de
tooling e os tipos exatos do contrato Core↔Adapter. Espere minha aprovação.

Depois: implemente a estrutura, o contrato em apps/api/src/leadflow/contracts/,
a suíte tests/contracts/ que todo adapter deve passar, o adapter de console e o
teste de arquitetura com import-linter. Documente o contrato em docs/03-contracts.md.
Termine com make test e make lint verdes.
```

---

### Fase 1 — Modelo de dados e multi-tenancy

**Objetivo:** schema Supabase completo com RLS, migrations e camada de repositório. Sem IA ainda.

**Contexto:** `docs/01-prd.md` §14, §15, §21, §22, §23; `docs/03-contracts.md`.

**Entregáveis:**
- Migrations: `organizations`, `org_members`, `agents` (config, instruções, ativo), `channels` (tipo, credenciais criptografadas, status), `knowledge_documents` + `knowledge_chunks` (pgvector), `products` (com `metadata jsonb`), `sellers`, `leads` (score, estágio, seller_id, resumo, próximo follow-up), `conversations`, `messages`, `scheduled_tasks`.
- RLS por `organization_id` em todas as tabelas; policies testadas.
- Repositórios Python tipados (sem ORM pesado; SQL explícito ou SQLModel leve).
- Seed com uma organização de demonstração.
- `docs/04-data-model.md` com diagrama Mermaid.

**DoD:** testes de RLS provam que a org A não lê dados da org B; seed roda; repositórios cobertos.

**Prompt de kickoff:**
```
Fase 1: modelo de dados. Leia docs/01-prd.md seções 14, 15, 21, 22 e 23 e
docs/03-contracts.md. Proponha o schema (tabelas, colunas, índices, RLS) em
docs/04-data-model.md com um diagrama Mermaid e espere aprovação.

Depois: crie as migrations em supabase/migrations/, os repositórios em
apps/api/src/leadflow/db/ e testes que provem o isolamento por organization_id
(uma org não enxerga a outra). Inclua seed de uma organização de demo.
Use o Supabase MCP para aplicar e validar as migrations.
```

---

### Fase 2 — AI Core v1 (agnóstico de canal)

**Objetivo:** o agente SDR funcionando de ponta a ponta pelo console adapter, com RAG, tools e regras de handoff. Esta é a fase que valida a tese do projeto.

**Contexto:** `docs/01-prd.md` §7, §9, §10, §12, §13; `docs/03-contracts.md`; skill `langgraph-core`.

**Entregáveis:**
- `core/llm/`: `LLMProvider` com implementação OpenAI (e Anthropic, se quiser as duas).
- `core/context/`: `OrgContextLoader` — monta system prompt a partir de agente + instruções + produtos + vendedores + regras da org.
- `core/rag/`: ingestão (chunking + embeddings → pgvector) e retrieval.
- `core/graph/`: LangGraph com nós `load_context → retrieve → reason → act(tools) → respond → persist`. Estado tipado (Pydantic).
- Tools: `search_knowledge`, `list_products`, `update_lead`, `set_stage`, `score_lead`, `schedule_followup` (só enfileira, Fase 4 executa), `handoff_to_human`.
- Regras de handoff (§9 do PRD) implementadas como nó explícito, não só no prompt.
- `tests/golden/`: 8–10 conversas de referência (lead frio, lead quente, pergunta fora da base, pedido de humano, assunto sensível, etc.) validadas por asserts estruturais (estágio final, tool chamada, handoff sim/não), não por texto exato.

**DoD:** `make golden` verde; pelo console, uma org de demo atende um lead, consulta a KB, registra o lead e escala quando deve.

**Prompt de kickoff:**
```
Fase 2: AI Core. Leia docs/01-prd.md seções 7, 9, 10, 12, 13 e docs/03-contracts.md.
Use a skill langgraph-core.

Proponha o grafo (nós, estado, tools) e a lista das 8–10 conversas golden em
docs/phases/phase-2.md. Espere aprovação.

Depois implemente core/llm, core/context, core/rag e core/graph. Regras de
handoff devem ser um nó explícito. O agente nunca afirma preço/produto/política
sem resultado de tool. Escreva os testes golden com asserts estruturais.
Valide tudo pelo console adapter. make golden e make test verdes.
```

---

### Fase 3 — Adaptador Telegram + provisionamento automático

**Objetivo:** o mesmo Core atendendo via Telegram, com bot criado e configurado automaticamente a partir do web app (nome e foto).

**Contexto:** `docs/03-contracts.md`; skill `channel-adapter`; skill `telegram-provisioning`.

**Entregáveis (em duas etapas):**
- **3a — Adapter:** `channels/telegram/` com webhook FastAPI, mapeamento `chat_id → lead`, mídia básica, passando a suíte `tests/contracts/`. Token inserido manualmente na org (para desbloquear testes cedo).
- **3b — Provisionamento:** serviço que, dado nome + foto, usa uma conta mestre (Telethon/Pyrogram) para `/newbot` no BotFather, guarda o token criptografado, chama `setMyName`, `setMyProfilePhoto`, `setMyDescription`, registra o webhook. Pool de contas mestre com rotação (limite ~20 bots/conta).

**DoD:** conversa real no Telegram com a org de demo; testes de contrato verdes; provisionamento cria um bot do zero em < 30s.

**Prompt de kickoff:**
```
Fase 3a: adapter Telegram. Leia docs/03-contracts.md e use a skill channel-adapter.
Implemente channels/telegram/ (webhook, mapeamento chat→lead, mídia básica) até
passar tests/contracts/. Token vem da tabela channels por enquanto.

Fase 3b (sessão separada): provisionamento automático. Use a skill
telegram-provisioning. Implemente o serviço que cria o bot via BotFather com
conta mestre, configura nome/foto/descrição via Bot API e registra o webhook.
Inclua pool de contas mestre e teste de integração marcado como @slow.
```

---

### Fase 4 — Fila de tarefas e follow-up temporizado

**Objetivo:** follow-ups, timeouts e retentativas rodando por Celery + Redis, com idempotência.

**Contexto:** `docs/01-prd.md` §6 (Agente SDR), skill `scheduled-tasks`.

**Entregáveis:**
- Celery app, worker e beat no `docker-compose`.
- `tasks/followup.py`: regra fixa configurável por org (ex.: 2h e 24h sem resposta); a task pede ao Core só o texto; cancela se o lead respondeu ou foi para humano.
- `tasks/timeouts.py`: conversas paradas → estágio "sem resposta".
- Idempotência por `scheduled_tasks.id`; retry com backoff; tudo logado.

**DoD:** teste de integração com relógio fake prova agenda/cancelamento; `schedule_followup` (tool da Fase 2) agora executa de verdade.

---

### Fase 5 — Web app (Next.js)

**Objetivo:** o gestor faz tudo pelo app: cria conta, configura agente, sobe conhecimento, cadastra produtos e vendedores, vê o CRM e assume conversas.

**Contexto:** `docs/01-prd.md` §6 (Autenticação, Configuração, Dashboard); skill `frontend-design` (pública) + `web-conventions`.

**Entregáveis (em ordem, cada uma testável):**
- 5a — Auth (Supabase Auth) + criação de organização + layout base.
- 5b — Configuração do agente (nome, instruções, ativar/desativar) + conectar canal Telegram (chama o provisionamento da Fase 3b).
- 5c — Base de conhecimento (upload/edição, status de indexação), produtos, vendedores.
- 5d — CRM: lista de leads, funil, detalhe com histórico, resumo da IA, atribuição de vendedor.
- 5e — Assumir conversa (pausa o agente naquela conversa) e responder manualmente.

**DoD:** fluxo completo do critério de sucesso do PRD §27 executável por uma pessoa sem tocar no backend; testes Playwright do caminho feliz.

**Prompt de kickoff (5a):**
```
Fase 5a: web app — auth e organização. Leia docs/01-prd.md seção 6 e use as
skills frontend-design e web-conventions. Estilo: limpo, direto, sem parecer
template — a referência de UX é "gerenciar o agente com a simplicidade de um
chat". Implemente login/cadastro com Supabase Auth, criação de organização e
o layout base com navegação. Teste Playwright do fluxo de cadastro.
```

---

### Fase 6 — Adaptador WhatsApp não-oficial (Evolution API)

**Objetivo:** segundo canal real, provando a modularidade. Fluxo de QR code no web app.

**Contexto:** `docs/03-contracts.md`; skill `channel-adapter`; skill `evolution-api`; `docs/00-pre-prd.md` §6 (riscos).

**Entregáveis:**
- `channels/evolution/`: instância isolada por org, webhook, QR code exposto ao web app, reconexão.
- Mitigações do risco de ban como código: só responde inbound, rate limit por número, "aquecimento" (limite progressivo nos primeiros dias), alerta de desconexão.
- Passa `tests/contracts/` sem mudar uma linha do `core/` — **esse é o teste da tese**.

**DoD:** a mesma org de demo atende pelo Telegram e pelo WhatsApp com o mesmo agente; diff em `core/` = zero.

---

### Fase 7 — Voz (Twilio) — spike condicional

**Objetivo:** decidir com evidência se entra no MVP. Timebox: 2 sessões.

**Entregáveis:** protótipo `channels/voice/` com Twilio Voice + STT/TTS (ex.: Deepgram/OpenAI Realtime ou Twilio ConversationRelay) respondendo uma pergunta simples via Core. Medir latência ponta a ponta. Registrar decisão em `docs/02-decisions.md`.

**DoD:** ADR escrita: "entra no MVP" ou "fica como visão futura", com números.

---

### Fase 8 — Hardening e deploy

**Entregáveis:** logs estruturados, tracing do agente (LangSmith ou Langfuse), contador de tokens por org, tratamento de falhas de integração, health checks, deploy (Railway/Render + Vercel), runbook em `docs/`.

**DoD:** ambiente de demonstração no ar e roteiro de demo do PRD §27 executado sem intervenção manual.

---

### Futuro (fora do ciclo) — Adaptador WhatsApp oficial (Meta Cloud API)
Mesma suíte `tests/contracts/`. Diferença principal: onboarding via Embedded Signup, não QR code.

---

## 5. Skills do projeto (`.claude/skills/`)

Skills são instruções reutilizáveis que o Claude Code carrega quando a tarefa bate com a descrição. Crie estas cinco; cada uma é um `SKILL.md` curto com checklist e exemplo.

| Skill | Quando dispara | Conteúdo essencial |
|---|---|---|
| `channel-adapter` | "criar/alterar adapter", "novo canal" | Passos para implementar `ChannelAdapter`; como mapear ids externos → lead; como rodar `tests/contracts/`; lista do que NÃO fazer (importar core internals, guardar credenciais em claro) |
| `langgraph-core` | qualquer mudança em `core/graph` ou tools | Convenções de nós e estado; como adicionar uma tool (schema Pydantic, registro, teste golden correspondente); regra "sem tool, sem afirmação comercial" |
| `supabase-migrations` | schema, migrations, RLS | Template de migration; policy RLS padrão por `organization_id`; como testar isolamento; nunca editar migration aplicada |
| `telegram-provisioning` | BotFather, tokens, webhook | Fluxo Telethon → BotFather → Bot API (`setMyName`, `setMyProfilePhoto`); rotação de contas mestre; criptografia de token |
| `scheduled-tasks` | follow-up, Celery, timeouts | Padrão de task idempotente; cancelamento; backoff; teste com relógio fake |
| `web-conventions` | qualquer arquivo em `apps/web` | App Router, Server Components por padrão, cliente Supabase, padrão de formulários, onde ficam os tipos gerados do banco |
| `evolution-api` | Fase 6 | Endpoints usados, formato do webhook, QR code, política de aquecimento e rate limit |

Skills públicas que valem instalar: **`frontend-design`** (Anthropic) para a Fase 5.

---

## 6. Subagents e hooks (`.claude/agents/`, `settings.json`)

**Subagents** (cada um é um `.md` com `name`, `description` e system prompt):
- `reviewer` — revisa o diff contra CLAUDE.md e docs/03-contracts.md; retorna lista de violações. Rode ao fim de cada fase: `use o subagent reviewer no diff desta fase`.
- `test-writer` — dado um módulo, escreve testes unitários e, se for do Core, propõe conversas golden novas.
- `docs-keeper` — atualiza `docs/phases/phase-N.md` e `docs/02-decisions.md` com o que mudou.

**Hooks** (em `.claude/settings.json`):
- `PostToolUse` em edições de `*.py` → `ruff check --fix` + `ruff format` no arquivo.
- `PostToolUse` em edições de `apps/api/src/leadflow/core/**` → `pytest tests/unit/test_architecture.py -q` (garante que o core não importou canal).
- `Stop` → `make lint` (avisa se algo quebrou antes de encerrar o turno).

**MCPs úteis:** Supabase (já conectado — migrations e consultas), GitHub (PRs), Context7 (documentação atualizada de LangGraph/Next.js — LangGraph muda rápido e o Claude Code precisa da versão certa), Playwright (Fase 5).

---

## 7. Como conduzir cada sessão (rotina que reduz erro)

1. `/clear` e abra a fase: `Leia CLAUDE.md e docs/phases/phase-N.md. Vamos começar.`
2. Peça o plano antes do código (os prompts acima já fazem isso). Corrija o plano — é mais barato que corrigir código.
3. Deixe o Claude Code implementar em blocos pequenos; entre blocos, `make test`.
4. Ao fim: `use o subagent reviewer`, depois `use o subagent docs-keeper`.
5. Commit + PR por fase. Não misture fases na mesma branch.
6. Se algo travar duas vezes no mesmo ponto, pare, registre uma ADR em `docs/02-decisions.md` e só então continue — o Claude Code repete o erro se a decisão não está escrita.

---

## 8. Sequência resumida

| Fase | Entrega | Prova |
|---|---|---|
| 0 | Repo + contratos + console adapter | contrato testado sem canal real |
| 1 | Schema + RLS | isolamento entre orgs |
| 2 | AI Core v1 | golden tests pelo console |
| 3 | Telegram + provisionamento | conversa real; bot criado do zero |
| 4 | Celery + follow-up | agenda/cancela com relógio fake |
| 5 | Web app | critério §27 do PRD sem tocar no backend |
| 6 | Evolution API | mesmo Core, diff zero em `core/` |
| 7 | Voz (spike) | ADR com números |
| 8 | Hardening + deploy | demo no ar |

Fases 0–3 entregam o MVP garantido (Telegram). Fases 4–5 fecham o critério de sucesso do PRD. Fase 6 prova a tese de modularidade. 7 e 8 são o que sobrar de tempo.
