# Progresso — LeadFlow.IA v1

## 2026-09-26T22:42:03Z — SL-D03: saudação sem handoff automático

- Evidência do usuário: “Olá” foi processado pelo GPT, virou `catalog_unsupported`/`awaiting_human` e não criou envio. Agora saudações recebem uma resposta curta de boas-vindas e perguntas sem suporte recebem orientação segura, sem transferir automaticamente; handoff explícito e pausa manual continuam preservados. API/worker/beat reiniciados; conversa do teste está `automatic`. Testes não executados após esta alteração; AC2 voltou a `not_run`.

## 2026-09-26T22:07:53Z — ambiente local zerado para repetir D0

- A pedido explícito do usuário, removidos os volumes PostgreSQL/Redis do projeto local, recriados serviços e reaplicadas migrations até 0057. Contagens de `auth.users`, organizações, produtos, vendedores, vínculos e mensagens Telegram: zero. Web/API/Auth locais 200, worker respondeu, HTTPS 200 e webhook gestor confirmado. Bots externos no Telegram permanecem; novo cadastro pode começar. `SL-D03` segue `in_progress`.

## 2026-09-26T21:58:38Z — SL-D03: gestor com várias contas e ambiente pronto

- Corrigido o onboarding para o mesmo gestor Telegram conectar bots distintos em empresas diferentes; migration 0057 aplicada com aprovação, preservando um único bot pendente por gestor. 11 testes Telegram, 91 Python, Ruff, mypy e diff passaram. API, worker e beat reiniciados; HTTPS 200, webhook do bot sem erro e fila pendente zero. Um bot conectado tem D0 ativo e um produto disponível. Usuário confirmou a criação do bot e iniciará a conversa real; AC1/AC4 seguem `not_run`, slice `in_progress`.

## 2026-09-26T21:02:11Z — SL-D03: implementação local concluída, prova real pendente

- Migrations 0053–0056, API, worker e painel adicionam ativação D0 explícita, consumo apenas de lotes posteriores à ativação, catálogo/OpenAI, sender Telegram e histórico com modelo, revisão e custo. `unknown` não é reenviado; pausa, opt-out e pedido humano bloqueiam resposta.
- Migration local aprovada e repetida. 89 testes Python, Ruff, mypy, lint, typecheck, build e 2 E2E Edge passaram; primeira suíte completa com worker/beat paralelos teve 2 falhas, resolvidas ao repetir isoladamente. Webhooks reais reconfigurados e HTTPS público 200. Usuário fará a mensagem/prova OpenAI real ao final; AC1/AC4 e `done` seguem pendentes. Sem commit ou avanço de slice.

## 2026-09-26T14:25:39Z — SL-D02: bot gerenciado real e entrada confirmados

- Gestor criou o bot pelo percurso no app; vínculo `connected`, identidade e webhook confirmados pela Bot API, com token cifrado. Uma mensagem Telegram real entrou e formou um lote `ready` após 5 segundos. HTTPS público recusou cabeçalho inválido (401), aceitou evento sintético (200) e persistiu replay uma vez. Quick Tunnel precisou ser recriado e os dois webhooks foram atualizados.
- Retomada após recarga, link direto de criação, atualização automática e falha por bot duplicado corrigidos. 9 testes Telegram, 1 E2E Edge, Ruff, mypy, lint e typecheck passaram; 84 Python passaram após a correção de retomada. Rotação validada isoladamente. Duas tentativas posteriores da suíte completa foram interrompidas por Control-C; build após a última mudança visual não foi executado para preservar a sessão web. `SL-D02` concluído no teste; V01/C01 e M1 permanecem parciais.

## 2026-09-25T20:10:32Z — SL-D02: webhook gestor registrado e guia local

- Token lido apenas do arquivo local ignorado; `telegram-webhook` confirmou `getMe`, `setWebhook` e `getWebhookInfo` reais para @LeadFlowAI_gestor_bot. API reiniciada com segredo; callback sintético autenticado retornou 200. Criado `doc-specs/start.md` com comandos de API, web, worker, beat, migrations e túnel. Suíte após migration 0051: 83 testes passaram, 1 aviso de depreciação. Bot gerenciado e callback reais ainda pendentes; SL-D02 permanece `blocked`.

## 2026-09-25T20:03:04Z — SL-D02: HTTPS temporário verificado

- Usuário autorizou Quick Tunnel sem cobrança; `cloudflared` já estava instalado. API local iniciada e `https://integrating-con-min-gonna.trycloudflare.com` encaminha à API (`/openapi.json` 200); callback sintético sem segredo retornou 401. URL salva em `.local/telegram.env` ignorado pelo Git; token ainda ausente. SL-D02 permanece `blocked` para webhook/bot reais, sem chamada OpenAI e sem avançar outro slice.

## 2026-09-25T19:35:42Z — SL-D02 parcial: bot gerenciado e buffer

- Pedido substituiu vínculo manual por onboarding self-service com bot gerenciado e buffer de 5 segundos; migrations locais autorizadas. Formulário, callbacks autenticados, vínculo/segredo cifrado, estado/retomada e lotes duráveis por chat implementados. Migrations 0049–0051 aplicadas e repetidas; 5 testes focados passaram após 0051, e 82 Python totais antes dela. Repetição total após 0051 foi interrompida pelo ambiente; Ruff, mypy, lint, typecheck e build passaram.
- Sem URL HTTPS pública ou token do bot gestor configurados, criação/webhook reais estão `blocked`. O lote ainda não é enviado à IA: consumo e resposta Telegram pertencem à integração posterior. SL-D02 permanece `blocked`, AC1–AC3 sem prova integral; SL-D03 não iniciado. Sem commit.

## 2026-09-25T16:54:45Z — SL-D01 concluído no canal de teste

- Após `429 billing_not_active` inicial, o usuário confirmou ativação do faturamento. O adaptador selecionou produto com `gpt-5.4-mini-2026-03-17`; quatro casos integrados reais com massa sintética passaram: zero → `R$ 0,00`, `null` → `Preço sob consulta`, ausente → fila humana, instrução maliciosa de preço → preço do catálogo. Replays conservaram runId. Estimativa total das oito chamadas bem-sucedidas: US$ 0,002043, abaixo de US$ 2; segredo não impresso.
- Primeira tentativa da suíte nesta retomada falhou por Auth local parado; `scripts/local.py prepare` iniciou PostgreSQL/Auth/Redis. Repetição: 78 testes Python, Ruff e mypy passaram. Migration 0048 repetida e 14 testes focados já haviam passado antes desta retomada. `git diff --check` e revisão dirigida passaram; E2E web não executado por ausência de mudança de interface. AC1–AC4 concluídos; SL-D02/SL-D03 não iniciados.

## 2026-09-25T16:13:31Z — SL-D01: arquivo local para chave OpenAI

- Criado `.local/openai.env` ignorado pelo Git, com `OPENAI_API_KEY=` vazio; `scripts/local.py` carrega a chave para os comandos locais. Teste com chave sintética passou, sem expor valor. `git diff --check` passou.
- Chamada OpenAI real continua `blocked` até o usuário preencher o arquivo; nenhuma chamada paga foi executada nesta retomada. SL-D01 permanece `in_progress`.

## 2026-09-25T16:01:47Z — SL-D01 parcial

- Mudança do catálogo entre preparação e sender agora cancela a intenção e encaminha a conversa humana. Migration 0048 aplicada e repetida; 14 testes focados do agente, 78 Python totais, Ruff e mypy passaram. OpenAI real permanece bloqueada pela ausência de `OPENAI_API_KEY`; critérios e slice seguem `in_progress`.

## 2026-09-25T15:56:32Z — SL-D01 parcial

- Modelo `gpt-5.4-mini-2026-03-17`, teto US$ 2, seams e migrations incrementais aprovados. Canal de teste prepara intenção sustentada por produto vigente, registra revisão/modelo/custo e encaminha ausência, indisponibilidade, desconto, seleção inválida ou falha do provedor. Sender cancela preparação comercial antiga. Nome duplicado no catálogo vigente agora retorna 409; quatro registros excedentes sintéticos desta sessão foram revogados com histórico preservado.
- 20 testes focados, 78 Python totais, Ruff, mypy e migrations repetidas passaram. Chamada OpenAI real `blocked`: `OPENAI_API_KEY` ainda indisponível; SL-D01 permanece `in_progress`, sem outro slice iniciado.

## 2026-09-24T20:13:39Z — SL-10: catálogo comercial versionado

- Gestor cadastra, corrige, remove e consulta produtos sintéticos no app. Migration 0041 guarda preço decimal exato ou `null`, disponibilidade, revisão comercial da empresa e versões imutáveis; API exige gestor e isola Alfa/Beta.
- Migration repetida, 5 testes focados, 63 da suíte, Ruff, mypy, lint, typecheck, build e 1 E2E Edge passaram. `SL-10/AC1`–`AC3` vinculados a SL10-API/WEB/PY; V09 completa, fontes documentais e resposta de IA seguem pendentes. Sem commit ou avanço de outro slice.

## 2026-09-23T11:13:51.2061227-03:00 — SL-00: preparação e implementação documental

- Estado inicial: branch `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`; seis arquivos-modelo, `state.json` sem revisões/slices. Não havia evidência nem aprovação registrada no harness.
- Alterações locais anteriores: RULES.md modificado; plano de slices e prompts/PROMPT-IMPLEMENTAR-SLICE.md não rastreados. Preservar esses conteúdos.
- Prontidão: pedido atual autoriza exclusivamente SL-00; seu bloco não tem dependências/bloqueadores documentais. Verificação de entrada: `ready`; início do trabalho: `in_progress`.
- Contexto carregado: RULES/AGENTS, CONTEXT, guias de validação/segurança, SL-00 completo, PRD RN-01/RN-12/§13.2, SPEC VAL-001/VAL-002/VAL-009 e skill TDD. Para indexar os demais slices, extraíram-se somente metadados, fontes, dependências e condições; nenhum foi iniciado.
- Alterações: preenchimento dos seis arquivos do harness, índice dos 35 slices e rastreabilidade documental. Nenhum código, dependência, serviço ou skill criado.
- Decisões: manter plano como baseline; evidências por critério no state. Outros slices continuam `planned`, sem autorização/prontidão presumidas. Não existe pausa HITL configurada para esta atualização.
- Verificações de preparação: Git, hashes e correspondência das fontes SL-00 inspecionados. O retrato antigo “sem commits” das fontes não foi usado como estado Git atual; hashes PRD/SPEC coincidem com os registrados no plano.
- Verificações finais/diff: ainda pendentes nesta entrada.
- Próximo passo: conferir coerência/JSON/links/grafo, simular retomada e revisar diff antes de registrar conclusão.

## Notação de evidência

Cada EV registra resultado observado e procedimento em state.json. A revisão de trabalho é o commit-base mais as alterações locais do harness nesta sessão, com hashes das fontes em sourceRevisions; não há commit de implementação criado.

## 2026-09-23T11:18:53.5900896-03:00 — SL-00: validação e encerramento

- Verificação focada: JSON analisado; 35 slices comparados ao plano; quatro critérios preservados; dependências anteriores sem ciclo; IDs encontrados em suas origens; 47 links/âncoras válidos (EV-01, passed).
- Preservação/revisões: nove hashes conferidos sem mudança, inclusive RULES/plano/prompt preexistentes; branch e commit-base registrados. Procedimento de invalidação por fonte e dependente documentado (EV-02, passed).
- Retomada: só SL-00 elegível durante execução; após done não há outro slice autorizado. SL-01 possui pacote mínimo e pendências explícitas de aprovação/V02/V05/seams (EV-03, passed).
- Revisão: conteúdo/diff dos seis arquivos conferido, metadados alinhados ao plano; `git diff --check -- .agents/harness` sem erros; não rastreados revisados, sem novo arquivo criado nesta tarefa (EV-04, passed).
- Verificações obrigatórias aplicáveis: coerência, referências e diff cumpridos. Guia de validação ainda sem comandos de aplicação; testes/lint/tipos/build/E2E de código `not_run`, não aplicáveis ao SL-00 documental (EV-05 passed; EV-06 not_run).
- Resultado: SL-00/AC1, AC2, AC3 e AC4 `passed`; status `done`. Nenhum código implementado nem outro slice iniciado. Evidência de documentação não certifica requisitos funcionais do produto.
- Limitações reais: avisos Git de ignore global e LF/CRLF; nenhuma alteração de configuração. Ocorrência de coleta JSON resolvida em feedback.
- Próximo passo: aguardar pedido específico para SL-01 e conferir condições de liberação antes de avançar.

## 2026-09-23T11:28:54.7045355-03:00 — SL-01: preparação bloqueada

- Pedido atual autoriza SL-01; SL-00 permanece done. Branch main/base 4f9e709; nove hashes de fontes preservados, sem divergência com o handoff.
- Preparação passed (SL01-PREP). Ambiente blocked (SL01-ENV): Python .venv 3.14.3 sem pip; Docker Engine indisponível também fora do sandbox; npm.cmd funciona. Sem manifests/testes/migrations encontrados na busca dirigida.
- Bloqueios: ambiente real de PostgreSQL/Auth, autorização de bootstrap/dependências, confirmação das seams e recorte V02/V05. Quatro critérios blocked; testes not_run (SL01-TESTS), nenhum código implementado.
- Atualizados state, este progresso, handoff e feedback. Mapa/README preservados: rastreabilidade não mudou. Próxima ação: resolver SL01-B1/B2/B3 e retomar exclusivamente SL-01.


## 2026-09-23T19:00:28.139Z — SL-01: implementação, validação e encerramento

- Estado inicial: SL-00 done; pedido atual e confirmação do usuário autorizaram exclusivamente SL-01. Dependência concluída; bloqueadores de ambiente e seams resolvidos nesta sessão.
- Red: suíte inicial falhou com 404 em POST /v1/organizations (SL01-RED). Green: 5 testes de integração passaram contra PostgreSQL/Auth locais sintéticos.
- Implementação: bootstrap local com Compose, Supabase Auth, roles sem bypass, RLS forced, migrations versionadas/checksum, função transacional de criação, idempotência e API autenticada; página Next.js mínima para cadastro e confirmação de agente/automação inativos.
- Validações: migration repetida; ruff/mypy Python; lint/typecheck/build web; diff check. Todos passaram. Warning de depreciação do TestClient/httpx permanece sem falha.
- Critérios: SL-01/AC1–AC4 passed, evidências SL01-GREEN/RLS/MIGRATION/PY/WEB. Testes externos/canais reais não executados e fora deste slice (SL01-EXT not_run).
- Resultado: SL-01 done. Nenhum slice posterior iniciado. Próximo passo: aguardar autorização específica para SL-02.

## 2026-09-23T19:23:39Z — SL-02: configuração e retomada

- Pedido autorizou somente SL-02; SL-01 done, fontes pertinentes sem mudança de hash e seams API/formulário confirmadas. V02 permanece pendente, por isso todos os checks não entregues e o checklist definitivo aparecem como pendências.
- Red: GET/PUT de configuração e POST de ativação retornaram 404 antes da implementação. Green: migration 0004, API autenticada com revisão otimista, impedimentos explícitos e formulário que recupera valores após recarga.
- Validação local sintética: migration repetida; testes Python de salvamento, conflito, sessão inválida, isolamento e ativação; ruff, mypy, lint, tipos, build e Playwright no Edge passaram. O primeiro build foi bloqueado pelo sandbox e passou fora dele; a primeira tentativa E2E encontrou navegador Playwright ausente e passou com Edge já instalado.
- Critérios SL-02/AC1–AC3 ligados a SL02-API/WEB/PY. Suíte final: 10 passed; ruff, mypy, lint e typecheck repetidos sem erro; diff revisado. Nenhum outro slice iniciado.

## 2026-09-23T20:15:01Z — SL-03: cadastro e acesso delimitado

- Pedido autorizou apenas SL-03; seams API/formulário confirmadas. Usuário definiu e-mail/telefone, senha inicial gerada e mostrada uma vez ao gestor e troca obrigatória. SL-01 done; fontes pertinentes sem mudança.
- Red/Green: cadastro, contato, habilitação, senha, revogação, disponibilidade e formulário falharam antes da implementação e passaram após migrations 0005–0012, RLS, API e UI. Falhas intermediárias de RLS/assinatura de rota e seletores E2E foram corrigidas e repetidas.
- Validação sintética: migration repetida, 12 testes Python, ruff, mypy, lint, typecheck, build e 2 E2E Edge passaram. SL-03/AC1–AC3 vinculados a SL03-API/WEB; diff revisado. Seleção/atribuição e fila V05 permanecem para slices futuros; nenhum outro slice iniciado.

## 2026-09-23T20:25:23Z — SL-04: entrada e histórico locais

- Pedido autorizou somente SL-04; usuário confirmou seams de entrada simulada e consulta pela API. Canal `telegram` é simulado, sem Bot API.
- Red 404 nas rotas ausentes. Migrations 0013–0016 criaram vínculo de canal com segredo, inbox, lead, conversa, mensagem, outbox e efeito de consumidor. Correções incrementais 0014–0016 preservam checksums já aplicados.
- PostgreSQL/Auth locais sintéticos: migration repetida, 17 testes Python, Ruff e mypy passaram. O teste de falha de persistência observou 503 sem histórico parcial; crash simulado após efeito da outbox gerou um único efeito na repetição. SL-04/AC1–AC4 vinculados a SL04-API.
- Diff e fontes revisados. Sem integração externa ou UI neste slice; nenhum outro slice iniciado.

## 2026-09-23T20:48:18Z — SL-05: pedido humano e fila do gestor

- Pedido autorizou apenas SL-05; usuário confirmou V05 para fila do gestor/atribuição manual sem prazo prometido e seams de entrada simulada, API e interface. Gatilho por lead pronto para conversão permanece para qualificação futura.
- Red relevante: fila e modo ausentes. Migration 0017, função transacional e API passaram a registrar pedido explícito, `awaiting_human`, estágio `handed_off`, incidente com gestor/ação e outbox/auditoria, sem depender de resumo ou modelo.
- Validação local sintética: migration repetida, 21 testes Python, Ruff, mypy, lint, typecheck, build e 3 E2E Edge passaram. SL-05/AC1–AC3 ligados a SL05-API/WEB. Nenhum outro slice iniciado.

## 2026-09-23 — SL-06: implementação parcial interrompida a pedido do usuário

- Pedido e seams confirmados exclusivamente para SL-06; SL-05 done. Migrations 0018–0021 aplicadas; claim, atribuição, concorrência e intenção manual 202 passaram em 4 testes focados (warning TestClient/httpx).
- Red mais recente: teste de aceitação do dispatcher falhou com 404 (4 passed, 1 failed). Migration 0022 foi escrita em seguida, ainda não aplicada nem testada. Validações finais e diff: not_run; critérios não concluídos.
- Handoff atualizado com arquivos, resultados, lacunas e próxima ação. Próxima sessão retoma o mesmo SL-06; nenhum slice posterior iniciado.

## 2026-09-24T13:57:25Z — SL-06: conclusão local

- Migration 0022 aplicada e repetida; API, canal simulado, incidente de confirmação perdida e interface de assunção/resposta concluídos. Fluxo do vendedor elegível incluído, preservando bloqueio por senha inicial.
- 10 testes focados e 31 na suíte Python passaram; Ruff, mypy, lint, typecheck, build e 1 E2E Edge passaram. Concorrência mantém uma intenção `dispatching` por conversa; rejeição e `unknown` não são reenviados; texto fora do limite recebe 422.
- SL-06/AC1–AC4 vinculados a SL06-API/WEB/PY/DIFF. Diff e fontes revisados; sem commit, canal externo ou avanço para SL-07.

## 2026-09-24T14:25:03Z — SL-07: controles na fronteira de envio

- Pedido específico, T01 e seams confirmados. Migrations 0023–0031 criaram simulação automática local, pausa/epoch, cancelamento de intenção pendente, assunção com conclusão pendente, retorno explícito à IA, bloqueio sintético e consulta de `controlId`; claim antigo perdeu EXECUTE para `app_api`. Ativação real permanece sujeita ao checklist existente.
- Pausa antes da preparação/autorização bloqueia saída; pausa ou claim durante dispatch retorna 202 e a conclusão mostra accepted/unknown sem cancelamento fictício. Reativação não remove modo humano/bloqueio; resposta manual continua permitida.
- Migration repetida, 44 testes Python, Ruff, mypy, lint, typecheck, build e 2 E2E Edge passaram. SL-07/AC1–AC4 ligados a SL07-API/WEB/PY/DIFF; fontes e diff revisados. Sem commit ou avanço para SL-08.

## 2026-09-24T14:49:53Z — SL-08: opt-out durável

- Migrations 0032–0033, API e UI registram origem por empresa/canal/contato, cancelam automação pendente, encaminham retorno à fila e preservam bloqueio em retry, nova conversa e reativação; T01 distingue tentativa externa em curso. V04 continua pendente, sem confirmação única ou reautorização.
- Migration repetida; 49 testes Python, Ruff, mypy, lint, typecheck, build e 1 E2E Edge passaram. SL-08/AC1–AC3 vinculados a SL08-API/WEB/PY/DIFF; diff e fontes revisados, sem commit nem avanço para outro slice.

## 2026-09-24T14:58:23Z — SL-09: análise e interrupção

- Dependência SL-08 e hashes PRD/SPEC/plano conferidos; escopo, FT-01/08/11 e caminhos atuais de outbox, dispatch e incidentes localizados. Redis/Celery locais sintéticos e seams API/conversa/canal aprovados pelo usuário (FB-12).
- Nenhum código, migration ou teste SL-09 alterado. Critérios e validações seguem `not_run`; estado `ready` para retomada exclusiva do slice nesta janela limitada.

## 2026-09-24T15:31:11Z — SL-09: implementação parcial interrompida

- Redis/Celery locais preparados; migrations 0034–0036 aplicadas, API de recuperação/incidentes e 3 testes focados passaram. Crash sintético deixa `dispatching`; varredura marca `unknown`, impede resultado tardio/reenvio, mostra dono e permite resolução com evidência sem declarar sucesso.
- Migration 0037 de worker foi escrita, **não aplicada/testada**; tarefa Celery, perda/reinício de broker, retries limitados, fencing explícito e gates finais faltam. Estado `in_progress`, AC1–AC4 sem comprovação integral; parada solicitada pelo usuário.

## 2026-09-24T19:22:46Z — SL-09: conclusão local

- Migrations 0037–0040 aplicadas incrementalmente e repetidas. Worker Celery com papel restrito varre registros duráveis, recupera `dispatching` vencido para `unknown` e reconstrói outbox após perda de mensagem Redis. Reserva durável e token rejeitam executor vencido; crash real após commit e antes do ack preservou efeito único no replay.
- Retry seguro de outbox usa até cinco tentativas com backoff/jitter, Retry-After e prazo total; esgotamento gera incidente com motivo, dono e próxima ação pela API. Outra conversa da mesma empresa continuou. Resolução de envio incerto conserva `unknown` e exige evidência.
- 58 testes Python, Ruff, mypy, lint/typecheck/build web e `git diff --check` passaram. Build inicial bloqueado por EPERM no sandbox passou na repetição autorizada. E2E web não executado porque não houve mudança de interface; canal externo e outros tipos de job futuros fora do escopo local.
- SL-09/AC1–AC4 vinculados a SL09-BROKER/PY/WEB/DIFF e evidência parcial anterior. Fontes preservadas, sem commit e sem avanço para outro slice.

## 2026-09-24T19:47:11Z — Replanejamento documental D0

- Pedido do usuário definiu apresentação em aproximadamente quatro dias com conta web, produtos, bot Telegram criado antes e vinculado no app, e modelo da API da OpenAI. PRD §5 e SPEC §1.4 registram D0 como marco parcial sem promover M1/M2, C01/C04 ou V01 a concluídos.
- Plano introduziu SL-D01–SL-D03 após SL-10 e manteve SL-11–SL-25 para completar documentos, avaliação do modelo, self-service e prontidão de M1. Dependências, mapa e state foram sincronizados; novos slices seguem `planned`, sem testes de aplicação ou integração externa nesta revisão.
- Modelo específico, credencial, orçamento, bot/token de teste, HTTPS e seams continuam como condições de liberação. Não foi criado código, dependência, serviço, commit ou skill nesta revisão documental.
- Verificação documental D0-PLAN: JSON legível; 38 slices, IDs únicos, dependências existentes e acíclicas, âncoras presentes; SL-D01–SL-D03 com dependências/Source IDs coerentes com o plano e fontes; nove hashes atuais e `git diff --check` sem divergência. O prompt não rastreado tinha hash diferente do registro anterior; conteúdo foi inspecionado e preservado, com revisão atual registrada sem alterar o arquivo.
