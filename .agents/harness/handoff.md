# Handoff — SL-10 catálogo comercial concluído

## Estado atual para retomada

- `SL-10` está `done` em `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, sem commit. Pedido específico e seams API/formulário/PostgreSQL confirmadas. Trabalho preexistente preservado; nenhum outro slice iniciado.
- Migration `0041_product_catalog.sql` adiciona revisão comercial por empresa, catálogo vigente e versões imutáveis por produto com RLS forced. API `/v1/orgs/{org}/products` cadastra/lista/corrige/revoga; `/versions` consulta histórico. Preço é string decimal de até quatro casas ou `null`; `0.0000` é válido. Correção/revogação avança revisão comercial, conflito 409 reverte a transação. Formulário do gestor em `apps/web/app/products.tsx` salva e recarrega.
- `SL-10/AC1`–`AC3`: SL10-API/WEB/PY. Migration repetida, 5 testes focados, 63 Python totais, Ruff, mypy, lint, typecheck, build e 1 E2E Edge passaram. O E2E inicial teve asserção textual incorreta; ajustada e repetida com sucesso. TestClient/httpx emite aviso de depreciação sem falha.
- Limites: catálogo estruturado sintético é a única fonte comercial de D0. V09 para múltiplas fontes, validação da resposta de IA, confronto de revisão antes do envio, documentos, modelo OpenAI e Telegram não foram executados neste slice. A API do catálogo hoje permite leitura ao gestor; consumidor futuro precisa de acesso confiável próprio sem ampliar a permissão do vendedor.
- Próxima ação: aguardar pedido específico de outro slice. Para SL-D01, ainda são condições modelo OpenAI específico, credencial/orçamento e seams; não inferir execução nem aceite a partir do catálogo.

## Registro anterior — plano D0 Telegram/OpenAI após SL-09

## Estado atual para retomada

- Usuário pediu replanejar a documentação para uma apresentação em aproximadamente quatro dias: criar conta no web app, cadastrar produtos, vincular bot Telegram criado previamente pelo usuário e mostrar atendimento com algum modelo da API da OpenAI. O pedido autoriza a revisão documental, não executa SL-10 ou SL-D01–SL-D03. Branch `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, sem commit novo e com working tree preexistente preservada.
- PRD §5 introduz D0 como demonstração parcial, sem substituir M1/M2; SPEC §1.4 fixa limites técnicos. O plano prioriza SL-10 → SL-D01 (catálogo/OpenAI em canal de teste) e SL-D02 (vínculo de bot preexistente no app) → SL-D03 (E2E Telegram). SL-11–SL-25 mantêm aceites completos, com dependências ajustadas para continuar após D0. Estado e mapa do harness contêm os três IDs novos como `planned`, `authorized=false`, `not_run`.
- Decisões já dadas: bot será criado antes e vinculado pelo app; provedor de IA será OpenAI. Ainda faltam modelo específico, credencial, orçamento, bot de teste/token por canal seguro, HTTPS alcançável e seams por slice. Token/chave não entram em código ou Git. V01/C01/C04 permanecem parciais porque a criação do bot ocorre fora do app; D0 não comprova M1.
- Próxima ação mínima: pedido específico para SL-10, com V09 delimitada ao catálogo sintético da demo e confirmação de seams de formulário/API; em paralelo, obter dados de ambiente para SL-D01/SL-D02 sem registrar segredos no harness. Nenhuma integração externa ou chamada paga foi executada nesta revisão documental.
- D0-PLAN passou: JSON legível, 38 slices sem IDs duplicados/dependências ausentes/ciclos/âncoras faltantes, três blocos D0 alinhados com state e Source IDs, nove hashes conferidos e `git diff --check` sem erro. O prompt não rastreado divergiu do hash anterior antes desta revisão; foi lido e preservado, com hash atual registrado. Testes de aplicação, bot real e OpenAI: `not_run` nesta revisão.

## Registro anterior — SL-09 concluído no ambiente local sintético

## Estado atual para retomada

- `SL-09` está `done` em `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, sem commit novo. Trabalho preexistente foi preservado. Os quatro critérios foram vinculados a SL09-BROKER/PY/WEB/DIFF e SL09-FOCUSED no `state.json`. Nenhum outro slice foi iniciado.
- Migrations incrementais 0034–0040 foram aplicadas e a migração repetida passou. `leadflow.recovery:celery_app` usa Redis local autenticado, payloads JSON com IDs, ack tardio, varredura periódica e papel `app_worker` com funções estreitas. Outbox recebe reserva durável e token de fencing; perda de mensagem Redis é reconstruída do PostgreSQL. `dispatching` vencido vira `unknown` com incidente, sem retry automático. Falhas internas seguras têm até cinco tentativas, backoff com jitter, limite de 60 s, Retry-After/prazo total e incidente ao esgotar; outra conversa pode seguir.
- Verificações executadas: 58 testes Python passaram, inclusive worker/broker/PostgreSQL reais locais, perda de mensagem de fila isolada, crash real do worker após commit antes do ack, replay sem duplicação, fencing, `unknown`, incidente e retries; Ruff e mypy passaram. Lint, typecheck e build web passaram. Build inicial falhou com EPERM no sandbox, repetido com autorização e aprovado. `git diff --check` passou; hashes de fontes conferidos. E2E web `not_run` por ausência de mudança de interface neste slice. Aviso de depreciação TestClient/httpx sem falha.
- Limite: as provas usam canal e massa sintéticos locais; nenhum provedor externo, IA real ou jobs de slices futuros foi exercitado. O teste de perda apaga apenas a fila Redis exclusiva criada por ele. Não afirmar entrega externa exatamente uma vez. Não avançar para SL-10 sem pedido específico.

## Registro anterior — SL-09 implementação parcial interrompida

## Estado atual para retomada

- Usuário solicitou parada imediata por limite da janela. `SL-09` está **in_progress**, não `done`; nenhum dos quatro ACs tem prova integral. Pedido e aprovações para Redis/Celery locais e seams API/conversa/canal permanecem válidos. Branch `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, sem commit novo; preservar working tree preexistente. Não avançar para SL-10.
- Código criado nesta retomada: `compose.yaml` com Redis autenticado/noeviction; `requirements.lock` com Celery 5.6.3/redis-py 8.1.0 e dependências; `scripts/local.py` gera segredos locais, cria papel `app_worker` sem bypass, oferece `worker`/`beat`; API tem crash sintético após início de dispatch, `POST /test-recovery/run`, GET de incidentes e POST resolve com evidência. Migrations `0034`–`0036` aplicadas ao PostgreSQL local, `0034` marca dispatch abandonado `unknown`, `0035` atribui dono do incidente, `0036` guarda resolução sem mudar a intenção de `unknown`. `0037_worker_watchdog.sql` foi escrita **depois**, mas **não aplicada nem testada**. Ela prepara funções estreitas para `app_worker`; revisar antes de aplicar. O módulo `leadflow.recovery:celery_app` **ainda não existe**, portanto os comandos `worker`/`beat` não funcionam até criá-lo.
- Verificações reais: Redis local foi iniciado e respondeu PING autenticado; Celery/redis-py instalados na `.venv`; migration 0034–0036 aplicada; 3 testes focados em `tests/integration/test_recovery.py` passaram após 0036. Suíte completa de 52 testes passou **antes** de 0035–0037. Mypy passou antes do último ajuste; Ruff apontou `timezone.utc`, trocado por `UTC`, mas Ruff **não foi repetido**. Migration 0037, worker/broker end-to-end, retries, full suite após última mudança, build/E2E e diff final: `not_run`.
- Próxima ação obrigatória: revisar/aplicar 0037 incrementalmente; criar `leadflow.recovery:celery_app` com payload JSON só de IDs, worker/beat locais e função de varredura durável. Recuperar trabalho elegível depois de perda do Redis; testar FT-01/08/11 com broker/banco reais e crash/reinício. Adicionar lease/fencing explícito, limites de retry/backoff/jitter/Retry-After/prazo e incidente ao esgotar; testar isolamento entre conversas e autorização da API. Não usar resultado `unknown` como sucesso ou reenvio seguro. Depois repetir migration, testes focados e suíte, Ruff, mypy, lint/typecheck/build/E2E aplicáveis, hashes/diff/status e atualizar critérios por evidência. Nenhuma política de negócio nova deve ser inventada.

## Registro anterior — análise sem implementação

## Estado para retomada do SL-09

- Pedido autoriza exclusivamente `SL-09`; `SL-08` está `done`. Branch `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, working tree amplo preexistente preservado, sem novo commit. Hashes de PRD/SPEC/plano conferidos contra `state.json`. Nesta janela, nenhum código, migration ou teste SL-09 foi escrito e nenhuma validação de implementação foi executada; AC1–AC4 permanecem sem evidência.
- O bloco exige watchdog de registros duráveis, recuperação de trabalho elegível, lease/fencing, `dispatching` abandonado → `unknown`, retries seguros limitados, incidentes com motivo/dono/próxima ação e isolamento entre conversas. Verificar FT-01, FT-08 e FT-11 com banco e broker reais; não declarar `done` com testes só de API simulada.
- Estado técnico existente: `compose.yaml` contém apenas PostgreSQL/Auth; `requirements.lock` e `pyproject.toml` não contêm Redis/Celery. `scripts/local.py` oferece prepare/api/web/test/migrate. A API publica outbox de teste (`private.consume_test_outbox`) e faz dispatch em duas transações (`private.authorize_test_dispatch`/`private.finish_test_dispatch`); `app.delivery_incidents` cobre confirmação perdida. Não há watchdog, lease/fencing ou worker/broker. Preservar migrations 0001–0033 aplicadas; usar migrations incrementais.
- Aprovações recebidas após a interrupção: usuário confirmou seams de operação de recuperação/incidentes pela API e efeitos observáveis na conversa/canal simulado; também aprovou adicionar Redis/Celery **locais sintéticos**. RULES.md §3 está satisfeito para essa dependência/serviço dentro do slice. Estado atualizado para `ready`; não pedir novamente essas confirmações. A interrupção precoce preserva a janela restante como o usuário solicitou.
- Próximo passo: fixar parâmetros técnicos testáveis conforme OPS-004/008/§4.12, desenhar recuperação idempotente por IDs duráveis e privilégios mínimos, executar red → green por FT-01/08/11 e C35/36/38. Cobrir crash antes de ack, perda de Redis, executor vencido, expiração conservadora de dispatching, Retry-After/prazo/limite e incidente; repetir migration, suíte, Ruff, mypy, web/E2E aplicável e diff. Não avançar para outro slice.

## Registro anterior — SL-08 concluído

## Estado para retomada

- `SL-08` está `done` em `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, sem commit novo. Pedido específico e seams de inbound, consulta da conversa e sender/saída simulada confirmados. `SL-07` permanece concluído; nenhum outro slice foi iniciado.
- Migrations incrementais `0032`–`0033` aplicadas e repetidas. `app.contact_opt_outs` conserva evento de origem por empresa/canal/contato; a entrada serializa pelo lock da organização antes da conversa. Pedido inequívoco cancela intenções automáticas pendentes e encaminha a conversa; novo chat do mesmo contato herda bloqueio e vai à fila humana. Retry não aplica texto alterado; reativação global e desbloqueio sintético não removem opt-out.
- Tentativa externa já em curso mantém resultado próprio: inbound retorna `202`, `control_applied=true`, `completion=pending_external_attempt`; não afirma cancelamento. Consulta da conversa e UI mostram motivo, origem e histórico; resposta manual continua disponível. Confirmação automática única e comando de reautorização continuam desabilitados até decisão V04.
- `SL-08/AC1`–`AC3`: SL08-API/WEB/PY/DIFF. 49 Python, Ruff, mypy, lint, typecheck, build e 1 E2E Edge passaram; teste de persistência consultou em outro processo. Warning TestClient/httpx sem falha. API/web do E2E encerrados e arquivos gerados pelo Next removidos. Canal real e política V04 `not_run`/pendentes; preservar o opt-out para consumidor futuro SL-23. Aguardar pedido específico para qualquer outro slice.

## Registro anterior — SL-07 concluído

## Estado para retomada

- `SL-07` está `done` em `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, sem commit novo. T01 foi aprovado pelo usuário: controle aplicado com tentativa externa em curso retorna `202`, `control_applied=true`, `completion=pending_external_attempt` e a UI informa “Controle aplicado; envio anterior em verificação”. As seams de comandos API, consulta na UI, sender e canal simulado foram confirmadas.
- Migrations `0023`–`0031` aplicadas e repetidas no PostgreSQL local. A ativação real continua recusada pelo checklist incompleto; intenção automática, bloqueio de contato e habilitação da simulação são locais e sintéticos. Pausa/claim e sender serializam por organização → conversa → intenção; controle `controlId` permite consultar conclusão `complete`, `unknown` ou ainda pendente. `app_api` perdeu EXECUTE no claim antigo e mantém o claim controlado (verificado no banco).
- `SL-07/AC1`–`AC4` passaram: SL07-API/WEB/PY/DIFF. Suíte Python 44 passed; Ruff, mypy, lint, typecheck, build e 2 E2E Edge passaram. Histórico, resposta manual e intenções canceladas foram preservados; retorno à IA simulada exige ação autorizada e elegibilidade atual.
- Canal real, follow-ups, opt-out definitivo e recuperação automática de `dispatching` abandonado não foram executados; pertencem a slices posteriores. API e web do E2E foram encerradas. SL-08 não foi iniciado.

## Registro anterior — SL-06 concluído

### Estado após SL-06

- `SL-06` está `done` em `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, sem commit novo. Somente SL-06 foi retomado; SL-07 não foi iniciado. Working tree preexistente amplo preservado.
- Migrations `0018`–`0022` aplicadas no PostgreSQL local sintético; `0022` repetida sem erro. Claim, atribuição, resposta manual, tentativa de entrega, saída do canal simulado e incidente para confirmação perdida estão implementados. O gestor e o vendedor elegível atribuído podem assumir e responder; o vendedor com senha inicial permanece bloqueado.
- `SL-06/AC1` a `AC4` passaram: SL06-API/WEB/PY/DIFF. Suíte Python 31 passed; Ruff, mypy, lint, typecheck, build e 1 E2E Edge passaram. Aviso de depreciação TestClient/httpx sem falha. `git diff --check` sem erro; fontes PRD/SPEC e bloco do slice sem alteração observada.
- `202` indica intenção `pending`; dispatch local serializa por conversa, grava tentativa antes da saída, distingue `accepted`, `rejected` e `unknown`. Repetir uma intenção conclusiva não reenvia; `unknown` cria incidente e avisa para verificar o canal. Aceitação não implica leitura.
- Limite: canal real, garantia de entrega externa exatamente uma vez e recuperação automática de `dispatching` abandonado não foram executados; permanecem fora do canal simulado deste slice. Não avançar automaticamente para outro slice. Serviços de API e web usados no E2E foram encerrados.

## Registro histórico — SL-06 parcial, substituído pelo estado acima

### Estado no momento da interrupção

- Branch `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, working tree preexistente amplo e sem commit novo. Pedido autorizou exclusivamente SL-06. O usuário confirmou as seams: POST de atribuição/claim/mensagem, GET de conversa/fila e dispatcher com canal simulado. As fontes pertinentes do SL-06 mantiveram seus hashes; apenas `prompts/PROMPT-IMPLEMENTAR-SLICE.md`, fora do slice, divergiu do hash anterior e foi preservado.
- `SL-05` continua `done`. SL-06 está **in_progress**; nenhum critério integral foi comprovado. Não avançar para SL-07. Usar o mesmo modelo, sem troca automática. Dados de teste sintéticos locais.
- Red/green executados: claim retornou 404 antes da rota; depois 403 por falta de privilégio de lock e passou com migration incremental. Assign retornou 404 antes da implementação e passou. Resposta manual retornou 404 antes da implementação e passou. Teste de concorrência observou um 200 e um 409. Última suíte focada antes do novo trabalho de dispatcher: 4 passed, 1 warning TestClient/httpx.
- Código já criado nesta sessão: `tests/integration/test_human_reply.py`, migrations `0018_human_claim.sql` a `0021_manual_intent.sql`, mudanças em `apps/api/src/leadflow/main.py`. Migrations 0018–0021 foram aplicadas ao PostgreSQL local. O teste mais recente de aceitação do dispatcher falhou com 404, red esperado (4 passed, 1 failed); migration `0022_simulated_dispatch.sql` foi escrita depois, **não aplicada nem testada**. Não alterar migrations já aplicadas; corrigir por arquivo incremental se necessário.
- Contrato já observado: claim do gestor sem atribuição; atribuição de vendedor elegível não assume; vendedor atribuído pode assumir; dois claims concorrentes deixam um responsável; POST de mensagem manual retorna 202/pending com autor e intenção no histórico, sem indicar leitura. Ainda faltam dispatcher, accepted/rejected/unknown, não reenvio, limite de texto, recusa/permissões, UI e validação final.
- Próxima ação mínima: retomar o mesmo SL-06, executar `scripts/local.py migrate` para 0022; implementar as rotas locais de dispatcher/consulta de saída, confirmar o teste red → green, depois escrever um comportamento por ciclo para rejected/unknown, reenvio e limite. Testar concorrência sender/claim e interface; executar suíte, Ruff, mypy, lint, typecheck, build, E2E aplicável, migration repetida e diff. Revisar privilégio/RLS e todo o diff antes de `done`.
- Verificações finais e revisão integral do diff: **not_run**. O teste de dispatcher: **failed** por rota ausente no red, não prova comportamento. O guia `docs-agents/validation.md` ainda tem comandos `[A DEFINIR]`; comandos existentes foram derivados do harness/scripts, sem inventar gate novo.

## Registro anterior — SL-05

## Estado atual

- `SL-05`: **done** em `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, working tree sem commit novo. Usuário confirmou pedido explícito neste slice, fila do gestor para atribuição manual sem prazo prometido e testes na entrada simulada/API/interface.
- A entrada de mensagem reconhece apenas frases inequívocas de pedido humano. Na mesma transação da inbox, `private.request_human_from_test_event` grava modo `awaiting_human`, estágio `handed_off`, motivo, incidente com gestor responsável/próxima ação, outbox e auditoria. Reentrega conserva um incidente. Não há chamada a modelo ou envio ao lead.
- `GET /v1/orgs/{org}/human-queue` e a página do gestor exibem a pendência e abrem o histórico. Resumo ausente é indicado como indisponível; o histórico permanece disponível. Migration `0017_human_handoff.sql`, API, componente `human-queue.tsx` e testes focados representam o contrato entregue.

## Critérios e validação

- [x] SL-05/AC1 — pedido humano sem qualificação grava motivo, `awaiting_human` e `handed_off`: SL05-API/WEB.
- [x] SL-05/AC2 — sem elegível, incidente aberto tem gestor responsável e ação manual; UI distingue pedido de assunção e não promete prazo: SL05-API/WEB.
- [x] SL-05/AC3 — sem resumo/modelo, histórico e fila ficam acessíveis e estado de conversa permanece para assunção futura: SL05-API/WEB.
- Migration aplicada/repetida; suíte Python 21 passed, Ruff, mypy, lint, typecheck, build e 3 E2E Edge passed. `git diff --check`, fontes e harness: SL05-DIFF. Warning de depreciação TestClient/httpx sem falha.

## Limites e próxima ação

- Dados sintéticos locais. Telegram externo, modelo real, seleção por qualificação e efetiva atribuição/assunção/resposta de vendedor `not_run` e fora do SL-05. V05 ficou decidido para a fila sem elegível; seleção automática e prazo operacional mais amplo seguem pendentes.
- Consumidores futuros devem preservar `mode`, incidente, motivo, ausência de resumo e histórico. Aguardar autorização específica de outro slice.

## Registro anterior — SL-04

## Estado atual

- `SL-04`: **done** no branch `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, working tree sem novo commit. O pedido autorizou somente este slice e o usuário confirmou entrada simulada autenticada e consulta do histórico pela API.
- `POST /v1/orgs/{org}/test-channels` cria vínculo local com segredo apresentado uma vez ao gestor; `POST /v1/test-channels/{channel}/events` aceita envelope normalizado, resolve a empresa pelo vínculo confiável, grava inbox/lead/conversa/mensagem/outbox atomicamente e ignora callbacks/eco. `GET /v1/orgs/{org}/conversations/{id}` entrega histórico mínimo ao gestor. Publicação simulada da outbox registra efeito durável e marca publicação em transação posterior.
- Migrations `0013`–`0016`, API em `apps/api/src/leadflow/main.py`, testes em `tests/integration/test_inbound_history.py`. Migrations 0014–0015 corrigem ambiguidade PL/pgSQL encontrada após aplicar 0013; 0016 separa efeito de confirmação da publicação para FT-02.

## Critérios e evidências

- [x] SL-04/AC1 — 2xx após commit; falha de persistência devolve 503 e rollback integral: SL04-API.
- [x] SL-04/AC2 — mesmo evento não duplica; evento diferente com texto igual permanece: SL04-API.
- [x] SL-04/AC3 — retomada no mesmo tenant/canal; homônimos, canais e empresas separados: SL04-API.
- [x] SL-04/AC4 — token do canal determina organização; crash simulado entre efeito e marcação da outbox conserva efeito único: SL04-API.
- `scripts/local.py migrate` repetido, `scripts/local.py test -q` (17 passed), Ruff e mypy: passed. `git diff --check`, status e fontes: SL04-DIFF. Warning de depreciação TestClient/httpx sem falha.

## Limites e próxima ação

- Massa e credenciais sintéticas locais. Canal `telegram`/`whatsapp_evolution` é apenas vínculo simulado; Bot API, Evolution, broker real e E2E web `not_run` e fora deste slice. Consulta retorna até 100 mensagens; paginação/cursor do CRM completo pertence a slice futuro. Nenhuma resposta automática ou mídia é processada.
- Preservar envelope, identidade `(organization_id, channel_id, external_user_id)` e IDs duráveis de inbox/outbox para sender/IA. Aguardar autorização específica de outro slice.

## Registro anterior — SL-03

## Estado atual

- `SL-03`: **done** no branch `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, sem novo commit. Pedido específico e confirmação das seams API/formulário autorizaram este slice.
- O gestor cadastra vendedor com nome, e-mail, telefone e disponibilidade sem criar vínculo. A habilitação cria conta no Auth local com senha aleatória mostrada uma vez; o vendedor precisa trocar a senha antes da elegibilidade. Ativo e disponível são controlados pelo gestor da mesma empresa; revogação de vínculo bloqueia o próximo comando com JWT ainda válido.
- API de sellers, vínculo, disponibilidade e troca de senha em `apps/api/src/leadflow/main.py`; migrations incrementais `0005`–`0012` com RLS forced e papéis sem bypass; formulário de gestor/vendedor em `apps/web/app/page.tsx` e `sellers.tsx`.

## Critérios, validação e limites

- SL-03/AC1: SL03-API/WEB — cadastro sem acesso, senha inicial sem persistência no app e troca obrigatória.
- SL-03/AC2: SL03-API/WEB — atualização de ativo/disponível limitada à empresa; vendedor não lê configuração global.
- SL-03/AC3: SL03-API/WEB — vínculo revogado nega nova consulta com o mesmo JWT.
- Migration repetida; 12 testes Python, Ruff, mypy, lint, typecheck, build, 2 E2E Edge e `git diff --check`: passed. Testes com contas e dados sintéticos locais; Auth hospedado e entrega real de credenciais `not_run`.
- A senha inicial é entregue fora do aplicativo pelo gestor; não há convite ou mensagem automática. Auth e banco não participam da mesma transação: se o vínculo falhar depois da criação da conta, a conta permanece sem acesso à empresa e requer tratamento operacional. V05 ainda precisa definir seleção/atribuição e responsável da fila para consumidores futuros.
- Próxima ação: aguardar autorização específica de outro slice. Preservar os contratos `SellerView`, elegibilidade e vínculo ativo para atribuição futura.

## Registro anterior — SL-02

## Estado atual

- `SL-02`: **done** no branch `main`, base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`, sem commit novo. Pedido autorizou exclusivamente SL-02; seams API e formulário confirmadas.
- Fontes de SL-02 conferidas por SHA-256 contra `sourceRevisions`; V02 segue pendente para checklist definitivo e prontidão de produção. Nenhum slice posterior foi iniciado.
- A migration `0004_agent_configuration.sql` adiciona nome, identidade e instruções ao agente, com atualização restrita ao gestor e revisão otimista. GET/PUT `/v1/orgs/{id}/agent-config` preservam progresso; GET `/agent/readiness` e POST `/agent/activate` expõem impedimentos sem ativar.
- O formulário salva, recarrega, mostra pendências e recupera conflito 409 buscando a revisão atual. Uma sessão expirada exige nova autenticação. A retomada manual usa e-mail, senha e ID da organização; a recarga usa a sessão local.

## Evidência e limites

- SL-02/AC1: SL02-API e SL02-WEB; salvamento não ativa e recarga conserva valores.
- SL-02/AC2: SL02-API e SL02-WEB; ativação incompleta retorna pendências e mantém instruções. Fonte comercial, canal, qualificação, contingência e V02 permanecem `pending`.
- SL-02/AC3: SL02-API; revisão antiga retorna 409 recuperável e token expirado não grava. Acesso de outra organização retorna 404.
- Migration repetida, suíte Python (10 passed), ruff, mypy, lint, typecheck, build e E2E Playwright no Edge local (1 passed): passed. `git diff --check` e consistência de fontes/evidências: passed. Dados sintéticos locais; infraestrutura hospedada e prontidão de produção `not_run`.
- Próxima ação: aguardar autorização específica de outro slice. SL-21 consome DTO `name`/`identity`/`instructions`/`version` e os checks pendentes; V02 precisa de decisão para checklist definitivo.

## Registro anterior — SL-01

## Estado atual

- Slice `SL-01`: **done**. Pedido explícito e confirmação posterior autorizaram exclusivamente este slice.
- Dependência SL-00: done; evidências EV-01 a EV-05 preservadas.
- Branch `main`; base `4f9e709d5c6cd380c7d7ff4ad51bc54cd5f955f6`; sem commit novo.
- Alterações preexistentes em RULES.md, doc-specs/implementation-slices.md, prompts/PROMPT-IMPLEMENTAR-SLICE.md e harness foram preservadas. Esta sessão adicionou apenas os arquivos do SL-01 e registros necessários.

## Resultado entregue

- Ambiente local sintético via [compose.yaml](../../compose.yaml): PostgreSQL 17.9 e Supabase Auth v2.196.0.
- API FastAPI autenticada em `/v1/organizations` e `/v1/orgs/{id}`; JWT valida issuer/audience/expiração; CORS local limitado.
- Criação atômica em função PostgreSQL SECURITY DEFINER estreita: organização, membro gestor, agente inativo e auditoria. Papéis `app_api`/ `app_bootstrap` não são superusuários nem bypass RLS; tabelas usam RLS forced.
- Idempotência por ator/operação/chave/hash com migrations 0001–0003 e lock transacional. Repetição igual retorna a mesma operação; corpo diferente retorna 409.
- Interface Next.js em [apps/web/app/page.tsx](../../apps/web/app/page.tsx), com labels, feedback `role=alert`, confirmação explícita de automação/agente inativos e dados sintéticos locais.

## Critérios comprovados

- [x] SL-01/AC1 — organização, gestor e agente inativo; repetição idêntica sem duplicação: SL01-GREEN, SL01-MIGRATION.
- [x] SL-01/AC2 — isolamento Alfa/Beta e sessão expirada: SL01-RLS, SL01-GREEN.
- [x] SL-01/AC3 — RLS forced, papéis reais, pool/contexto e rejeição sem persistência parcial: SL01-RLS, SL01-GREEN.
- [x] SL-01/AC4 — migrations repetíveis e verificações: SL01-MIGRATION, SL01-PY, SL01-WEB.

## Verificações executadas

- `python scripts/local.py migrate` repetido no banco local: passed.
- `python scripts/local.py test -q`: 5 passed, 1 warning de depreciação TestClient/httpx.
- `python -m ruff check apps/api/src scripts tests`: passed.
- `python -m mypy apps/api/src`: passed.
- `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run build` em apps/web: passed.
- `git diff --check`: passed.
- Testes externos Supabase hospedado, canais reais e E2E de navegador: not_run, fora do escopo do SL-01.

## Pendências e limites

- Os testes usam usuários, organizações e credenciais sintéticos locais; não comprovam infraestrutura hospedada ou política de dados de produção.
- A migration 0003 documenta a correção de privilégio observada durante o Green.
- Não há vendedores, canais, prontidão comercial, ativação do agente ou schema de funcionalidades futuras neste slice.
- Nenhum slice posterior foi iniciado. Aguardar autorização específica para SL-02.
