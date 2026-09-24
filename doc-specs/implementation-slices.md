# Slices de implementação — LeadFlow.IA v1

Documento de planejamento iniciado em 23/09/2026 e reordenado para a demonstração D0 em 24/09/2026. O plano por si não comprova implementação: SL-00–SL-09 já têm evidências no harness, e critérios futuros permanecem abertos. D0 é parcial; M1/M2 conservam seus aceites completos.

## Fontes e limites

- **PRD:** [PRD-v1.md](PRD-v1.md), versão 1.1 com decisão D0 documentada. SHA-256: `b8915ac4fa7ff61268da5315ee96e510c41c45d32db1cc44665e96eed16643cf`.
- **SPEC:** [spec-v1.md](spec-v1.md), versão 1.1 com perfil técnico D0. SHA-256: `374a85814a2a8d2fa793d3d482901342b04391494d409a99c7b9fd600970ada3`.
- [Template](templates/implementation-slices.template.md): referência apenas da organização em resultado, dependências, escopo, aceite, verificação e handoff.
- [Harness existente](../.agents/harness/README.md): estado/evidências reais dos slices concluídos e pendências dos slices planejados; a revisão D0 deve manter o grafo e os hashes sincronizados.
- [Regras](../RULES.md) e [validação](../docs-agents/validation.md) continuam aplicáveis. Comandos de aplicação ainda não foram preenchidos no guia; resultados efetivamente executados constam do harness, sem inventar gates.
- Git observado nesta elaboração: branch `main`, commit abreviado `4f9e709`, sem alterações reportadas inicialmente por `git status --short`. Houve aviso de acesso negado ao ignore global. O retrato antigo “sem commits” presente nas fontes não foi herdado como estado atual.
- `CONTEXT.md` ainda é modelo; usa-se o vocabulário real do PRD §6 e da SPEC §2 sem preenchê-lo nesta tarefa.

`SL-00…SL-34` e `SL-D01…SL-D03` são identificadores locais deste plano, **não Source IDs do produto**. Não equivalem às fatias `S00…S07` da SPEC §10.1. Os três slices D0 atravessam catálogo, modelo e canal para a apresentação; os blocos originais mantêm o aceite M1/M2. Requisitos, cenários, restrições e decisões mantêm seus IDs originais nos campos **PRD:** e **SPEC:**.

A ordem do índice prioriza D0 após SL-10 e depois retoma o caminho de M1/M2. “Depende de” lista arestas diretas; dependências transitivas são herdadas. Um item posterior com dependência anterior já satisfeita pode ser antecipado somente preservando suas condições de liberação. A cronologia não é estimativa de prazo nem garantia de entrega em quatro dias. SL-00, spikes SL-19/SL-26 e gates são entregas documentais/de validação explícitas; os slices de produto atravessam entrada, regra/persistência e resultado observável.

## Contexto por slice: Smart Zone, Context Graph e retomada

Smart Zone/Dumb Zone é uma heurística de trabalho: contexto acumulado, irrelevante ou contraditório pode degradar o desempenho antes de atingir o limite da janela. Usar uma tarefa focada por sessão e um handoff pequeno é a aplicação adotada aqui; não se estabelece percentual ou limiar universal de tokens. Referência primária: [Matt Pocock — Smart zone](https://github.com/mattpocock/dictionary-of-ai-coding/blob/main/dictionary/Smart%20zone.md).

O estudo [Lost in the Middle](https://arxiv.org/abs/2307.03172) observou pior recuperação de informação relevante no meio de contextos longos nos modelos/tarefas avaliados. A organização abaixo é uma medida prática para reduzir esse risco, sem prometer eliminá-lo.

**Grafo documental proposto:** `PRD:regra/cenário → SPEC:REQ/AC/contrato → SL-xx → seam/código → teste/evidência`. As arestas `SL-xx → dependência direta` e `decisão pendente → slice afetado` orientam o carregamento. Não exige banco de grafos nem novo produto. Source IDs têm namespace por arquivo; um Cxx citado dentro da SPEC continua sendo cenário de origem PRD, não ganha identidade SPEC.

1. No início da sessão, consultar estado Git e harness; selecionar um único slice autorizado, incompleto e desbloqueado.
2. Abrir **este bloco**, trechos indicados das fontes e contratos/handoffs das dependências diretas. Não carregar o plano inteiro, histórico completo de sessões ou todos os arquivos de código.
3. No topo do contexto de execução, manter resultado, restrições, Source IDs e decisões ainda abertas. Usar o mapa de impacto para buscar somente os arquivos e evidências pertinentes.
4. Trabalhar um comportamento por ciclo. Se o slice não couber numa sessão focada, registrar o ponto de parada e a próxima ação observável; subdividir o trabalho mantendo os mesmos vínculos de origem, sem ampliar requisitos.
5. Antes de fechar, recolocar em foco os Acceptance Criteria e registrar resultados, revisão e próxima ação no handoff. Sinais de repetição, esquecimento de restrições ou pressupostos contraditórios pedem revisão do pacote e retomada em contexto limpo, não mais histórico indiscriminado.
6. Mudança de PRD/SPEC/política/contrato exige comparar revisões e revisar somente nós dependentes. Evidência antiga deve indicar sua versão; não migra automaticamente para “válida” na nova revisão.

Cada **Handoff** abaixo é o conteúdo específico a produzir. Em todos, acrescentar: branch/revisão e alterações locais; contrato efetivamente confirmado; caminho do teste/artefato, procedimento, esperado/observado e revisão; distinção entre aprovado, reprovado, bloqueado e não executado; decisões pendentes e próxima ação mínima. Atualizar os arquivos do harness no ciclo futuro, sem reproduzir logs extensos nem segredos.

## Disciplina de execução e verificação

As seams de cada slice são **propostas, ainda não confirmadas pelo usuário**. Conforme a skill TDD, antes de escrever testes no futuro, registrar e confirmar as fronteiras do slice com o usuário. Essa confirmação não é necessária para elaborar este plano, que não escreve testes.

Após a confirmação: um teste comportamental falha (**red**), a implementação mínima o faz passar (**green**), e só então se escolhe o próximo comportamento. Não escrever toda a suíte antes da implementação. Refatoração pertence à revisão posterior segundo a skill. Verificar via interfaces públicas; doubles somente nas fronteiras externas e no tempo. Para RLS, transações e locks, confirmar expressamente a fronteira PostgreSQL e usar papéis reais, sem usar consultas laterais para comprovar comportamento que deveria ser observado pela API.

Todas as capacidades novas já nascem com autorização, isolamento, auditoria e estados de erro pertinentes. As validações finais integram evidências incrementais, não adiam segurança até o fim. Lint, tipos, build, contratos e verificações de migration aplicáveis entram conforme o percurso é criado; comandos reais são registrados após validação. Teste fake não substitui prova de modelo/canal real. Usar apenas massa sintética.

As decisões V01–V09/T01 bloqueiam o aceite correspondente conforme PRD §14 e SPEC §1.3/§4.9. Políticas sintéticas podem apoiar testes isolados quando as fontes permitem, sempre rotuladas; não aprovam produto nem liberam integração/custo/infraestrutura por implicação. V10/voz permanece fora desta série obrigatória.

## Índice cronológico e dependências

| Slice | Resultado focal | Depende de |
| --- | --- | --- |
| [SL-00](#sl-00) | Criar a série documental do harness | Nenhum slice |
| [SL-01](#sl-01) | Criar conta e organização isolada | SL-00 |
| [SL-02](#sl-02) | Salvar configuração e retomar onboarding | SL-01 |
| [SL-03](#sl-03) | Cadastrar vendedores e habilitar acesso delimitado | SL-01 |
| [SL-04](#sl-04) | Receber contato e consultar histórico sem duplicar | SL-01 |
| [SL-05](#sl-05) | Pedir humano e aparecer na fila com contexto | SL-03, SL-04 |
| [SL-06](#sl-06) | Assumir e responder pelo canal simulado | SL-05 |
| [SL-07](#sl-07) | Aplicar pausa e prioridade humana na fronteira de envio | SL-02, SL-06 |
| [SL-08](#sl-08) | Persistir opt-out e encaminhar novo contato bloqueado | SL-07 |
| [SL-09](#sl-09) | Recuperar trabalho interrompido sem repetir envio incerto | SL-08 |
| [SL-10](#sl-10) | Manter catálogo comercial versionado | SL-02 |
| [SL-D01](#sl-d01) | Responder sobre o catálogo com OpenAI no canal de teste | SL-05, SL-09, SL-10 |
| [SL-D02](#sl-d02) | Vincular no app um bot Telegram preexistente | SL-02, SL-04, SL-09 |
| [SL-D03](#sl-d03) | Demonstrar atendimento Telegram ponta a ponta | SL-08, SL-D01, SL-D02 |
| [SL-11](#sl-11) | Disponibilizar documento com estado e recuperação de falha | SL-10 |
| [SL-12](#sl-12) | Responder com fonte válida ou encaminhar a dúvida | SL-11, SL-D01 |
| [SL-13](#sl-13) | Invalidar fonte e preparação de resposta antiga | SL-12 |
| [SL-14](#sl-14) | Coletar fatos, receber mídia e preservar correções | SL-12 |
| [SL-15](#sl-15) | Configurar rubrica e qualificar com evidências | SL-14 |
| [SL-16](#sl-16) | Corrigir classificação e concluir oportunidade por pessoa | SL-07, SL-15 |
| [SL-17](#sl-17) | Consultar CRM, resumo e redistribuir responsabilidade | SL-03, SL-16 |
| [SL-18](#sl-18) | Validar atendimento com modelo real versionado | SL-13, SL-15, SL-17, SL-D01 |
| [SL-19](#sl-19) | Validar a experiência self-service do Telegram | SL-00 |
| [SL-20](#sl-20) | Conectar Telegram e retomar provisionamento | SL-19, SL-D02 |
| [SL-21](#sl-21) | Ativar e atender a primeira conversa no Telegram | SL-18, SL-20, SL-D03 |
| [SL-22](#sl-22) | Configurar política e enviar um follow-up elegível | SL-15, SL-21 |
| [SL-23](#sl-23) | Cancelar follow-up e respeitar janela, validade e limite | SL-16, SL-22 |
| [SL-24](#sl-24) | Consultar operação e indicadores com custo explícito | SL-17, SL-23 |
| [SL-25](#sl-25) | Comprovar o marco M1 no Telegram | SL-24 |
| [SL-26](#sl-26) | Comprovar contrato da release Evolution | SL-25 |
| [SL-27](#sl-27) | Conectar WhatsApp e renovar QR expirado | SL-26 |
| [SL-28](#sl-28) | Atender no WhatsApp com o mesmo domínio | SL-27 |
| [SL-29](#sl-29) | Recuperar WhatsApp sem interromper Telegram | SL-28 |
| [SL-30](#sl-30) | Comprovar M2 e fechar cobertura multicanal | SL-29 |
| [SL-31](#sl-31) | Medir carga, justiça e custo antes do piloto | SL-30 |
| [SL-32](#sl-32) | Aplicar política de dados e exclusão com jobs pendentes | SL-30 |
| [SL-33](#sl-33) | Restaurar operação com automação inicialmente bloqueada | SL-31, SL-32 |
| [SL-34](#sl-34) | Revisar prontidão documental e operacional do piloto | SL-33 |

<a id="sl-00"></a>

## SL-00 — Criar a série documental do harness

**Resultado esperado:** Uma sessão nova consegue identificar o próximo trabalho autorizado e reconstruir seu contexto sem reler toda a conversa.

**Depende de:** nenhum slice.

**Condições de liberação / bloqueios:** Nenhuma para documentar; a execução futura dos slices depende das aprovações indicadas nas fontes.

### Source IDs e contexto mínimo

**PRD:** RN-01; RN-12.

**SPEC:** VAL-001; VAL-002; VAL-009.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9, 13.2 → obrigações/contratos da [SPEC](spec-v1.md) §10.2 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. O pedido atual e o README do harness são a origem específica desta entrega documental; os IDs de produto fundamentam rastreabilidade e evidência, não inventam um requisito de harness.

### Escopo

Criar o conteúdo operacional nos arquivos já existentes em `.agents/harness`: README com o ciclo de retomada; state.json com revisões das fontes e slices; impact-map.md com relações de origem/implementação/verificação; progress.md com registro cronológico; feedback.md com falhas e ações; handoff.md com estado, contratos, evidências, riscos e próxima ação. Preservar registros existentes. A criação aqui é da série preenchida e coerente, pois os arquivos-base já existem.

### Fora de escopo

Bootstrap técnico, criação de skills, alteração de PRD/SPEC e decisão de produto.

### Acceptance Criteria

- [ ] Os seis arquivos descrevem o mesmo estado real, sem marcar implementações ou testes não realizados como concluídos.
- [ ] Cada slice possui referência independente ao PRD e à SPEC, dependências diretas e próxima ação; o mapa distingue cobertura planejada de evidência executada.
- [ ] Revisões das fontes, branch e revisão Git são registradas a partir da inspeção atual; mudanças de origem indicam quais relações precisam de revisão.
- [ ] Uma retomada documental permite selecionar trabalho desbloqueado e reconstruir o pacote mínimo; pendências de produto e seams ainda não confirmadas continuam explícitas.

### Testes / verificação

Fronteira documental: simular leitura de README → state → handoff → bloco de um slice → fontes diretas; conferir JSON, referências e coerência dos registros. Sem testes de aplicação.

### Handoff

Série documental navegável, procedimento de atualização e primeiro pacote de contexto para SL-01; registrar que nenhum código foi implementado.

<a id="sl-01"></a>

## SL-01 — Criar conta e organização isolada

**Resultado esperado:** Gestor cria conta/empresa pelo aplicativo e volta a consultar somente sua operação.

**Depende de:** [SL-00](#sl-00).

**Condições de liberação / bloqueios:** PRD/SPEC/slice aprovados; V02/V05 para regras finais de acesso. Dependências e ambiente sujeitos às regras do repositório.

### Source IDs e contexto mínimo

**PRD:** US-01; US-02; US-34; RN-01; C01; C02; C07; V02; V05.

**SPEC:** REQ-001; AC-001; SEC-001; SEC-002; SEC-003; DAT-001; DAT-004; FT-09; ARC-002; GUD-002; PLT-001.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§6, 9, 12.2 → obrigações/contratos da [SPEC](spec-v1.md) §§3.4–3.5, 4.1, 4.3–4.5, 6.4 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Entregar o percurso cadastro/autenticação → API → organização, vínculo gestor e agente inativo → leitura web. Introduzir apenas runtimes, contratos gerados, migrations e CI necessários a esse percurso, com versões compatíveis fixadas.

### Fora de escopo

Schema de funcionalidades futuras e provisionamento de canais.

### Acceptance Criteria

- [ ] Criação atômica produz uma organização, gestor e um agente inativo; repetir comando idêntico não duplica a operação.
- [ ] Alfa não lê nem altera Beta por troca de identificador; sessão expirada não altera dados e solicita autenticação.
- [ ] RLS usa papéis reais sem bypass; conexão reutilizada e contexto ausente não expõem outra organização; falha na criação não deixa organização parcial.
- [ ] Instalação/upgrade das migrations do percurso e verificações existentes no CI ficam reproduzíveis, com comandos efetivamente validados no handoff.

### Testes / verificação

Seams propostas: cadastro/login e API de organizações; PostgreSQL como fronteira específica de autorização/transação, a confirmar. Primeiro ciclo: criar e recuperar organização; depois negações C02/C07 e FT-09.

### Handoff

Contrato de identidade/organização, papéis de teste Alfa/Beta, cliente gerado, comandos comprovados e limitações de V02/V05.

<a id="sl-02"></a>

## SL-02 — Salvar configuração e retomar onboarding

**Resultado esperado:** Gestor salva identidade/instruções e retoma a configuração sem perder progresso.

**Depende de:** [SL-01](#sl-01).

**Condições de liberação / bloqueios:** V02 para checklist definitivo; configuração sintética não comprova prontidão de produção.

### Source IDs e contexto mínimo

**PRD:** US-03; US-04; US-12; RN-02; C03; C07; V02.

**SPEC:** REQ-002; AC-002; CON-008.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§7/J01, 9 → obrigações/contratos da [SPEC](spec-v1.md) §§4.1, 4.3 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Formulário → comandos versionados → configuração persistida → checklist legível. Exibir pré-condições ainda ausentes das capacidades não entregues.

### Fora de escopo

Ativação real, políticas inventadas e preenchimento de CONTEXT.md.

### Acceptance Criteria

- [ ] Salvar não ativa o agente; reabrir a tela preserva os valores confirmados.
- [ ] Ativação incompleta identifica impedimentos e conserva instruções; nenhum check ausente é tratado como aprovado.
- [ ] Atualização concorrente retorna conflito recuperável; sessão inválida não grava alteração.

### Testes / verificação

Seams propostas: API de agente/readiness e formulário. C03 e C07 por resultado observável, incluindo recarga e conflito de versão.

### Handoff

DTO de configuração, semântica de revisão e checks pendentes consumidos em SL-21.

<a id="sl-03"></a>

## SL-03 — Cadastrar vendedores e habilitar acesso delimitado

**Resultado esperado:** Gestor cadastra disponibilidade e distingue vendedor cadastrado de usuário habilitado.

**Depende de:** [SL-01](#sl-01).

**Condições de liberação / bloqueios:** V05 para habilitação, permissões, elegibilidade e responsável da fila.

### Source IDs e contexto mínimo

**PRD:** US-09; US-23; RN-01; RN-08; C02; V05.

**SPEC:** REQ-001; REQ-008; SEC-001; AC-001.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§6, 9 → obrigações/contratos da [SPEC](spec-v1.md) §§4.3–4.5, 4.10 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Cadastro web → persistência → consulta de elegibilidade; fluxo de habilitação autenticada conforme V05, usando convite sintético se essa proposta for aprovada.

### Fora de escopo

Envio de convites reais e distribuição automática não aprovada.

### Acceptance Criteria

- [ ] Cadastro isolado não concede login nem papel; habilitação segue identidade e política aprovadas.
- [ ] Ativo/disponível e vínculo pertencem à mesma empresa; vendedor não altera configurações globais.
- [ ] Revogação de vínculo impede o próximo comando mesmo com JWT ainda válido.

### Testes / verificação

Seams propostas: sellers e habilitação/membership. Testar cadastro sem acesso, vínculo cruzado, revogação e convite expirado/reutilizado se adotado.

### Handoff

Regra aprovada de elegibilidade, identidades sintéticas e autorização reutilizável por atribuição/assunção.

<a id="sl-04"></a>

## SL-04 — Receber contato e consultar histórico sem duplicar

**Resultado esperado:** Uma entrada pelo canal de teste cria um contato/histórico consultável e uma reentrega conserva esse registro.

**Depende de:** [SL-01](#sl-01).

**Condições de liberação / bloqueios:** Contrato normalizado da SPEC §4.2; adaptador simulado somente para desenvolvimento.

### Source IDs e contexto mínimo

**PRD:** US-18; RN-05; RN-07; RN-12; C17; C18; C35.

**SPEC:** REQ-005; REQ-007; REQ-012; AC-005; CON-001; CON-004; SEC-005; OPS-001; FT-02.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9–10, 12.3, 12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.2, 4.5–4.6, 4.12 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Entrada autenticada/normalizada → inbox, mensagem e outbox atômicas → histórico mínimo no CRM. Implementar apenas entidades necessárias; separar callbacks de conexão/eco de mensagens inbound.

### Fora de escopo

Resposta automática, interpretação de mídia e integração externa.

### Acceptance Criteria

- [ ] Confirmar recebimento somente após persistência; falha de banco não produz sucesso nem histórico parcial.
- [ ] Reentrega do mesmo evento não duplica lead/mensagem/trabalho; evento distinto com texto igual permanece válido.
- [ ] Contato retoma o histórico no mesmo tenant/canal; homônimos e contatos em empresas/canais distintos não são fundidos.
- [ ] Repetição de publicação da outbox não duplica efeito; origem da organização vem do vínculo confiável.

### Testes / verificação

Seams propostas: webhook/ChannelAdapter e leitura de conversa. C17/C18/C35 e FT-02 com PostgreSQL real e transporte simulado.

### Handoff

Envelope inbound, identidade local, consulta do histórico e massa de reentrega para sender/IA.

<a id="sl-05"></a>

## SL-05 — Pedir humano e aparecer na fila com contexto

**Resultado esperado:** Lead pede uma pessoa e gestor encontra a conversa suspensa com motivo e histórico.

**Depende de:** [SL-03](#sl-03), [SL-04](#sl-04).

**Condições de liberação / bloqueios:** V05 para responsabilidade da fila; primeiro percurso usa solicitação inequívoca, sem depender do modelo.

### Source IDs e contexto mínimo

**PRD:** US-19; US-23; US-29; RN-08; C21; C22; C23; V05.

**SPEC:** REQ-008; AC-008; CON-003.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§7/J04, 9, 12.4 → obrigações/contratos da [SPEC](spec-v1.md) §§4.3, 4.10, 9.4 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Entrada reconhecida → comando atômico de encaminhamento → aguardando humano/atribuição ou incidente → fila no aplicativo. Resumo é opcional e posterior.

### Fora de escopo

Detecção semântica completa dos gatilhos e geração de resumo.

### Acceptance Criteria

- [ ] Pedido humano não exige qualificação completa; registra motivo e suspende automação na conversa.
- [ ] Sem elegível, fila tem responsável de tratamento e próxima ação; não promete humano imediato nem retorna sozinho à IA.
- [ ] Falha/ausência de resumo preserva histórico e não impede encaminhamento/assunção futura.

### Testes / verificação

Seams propostas: entrada inbound e fila/conversa na API/UI. C21 no gatilho explícito, C22/C23 com modelo indisponível.

### Handoff

Comando de handoff e projeção da fila, reutilizados para gatilhos de IA em SL-12/SL-15.

<a id="sl-06"></a>

## SL-06 — Assumir e responder pelo canal simulado

**Resultado esperado:** Pessoa autorizada assume e acompanha o resultado de sua resposta manual no histórico.

**Depende de:** [SL-05](#sl-05).

**Condições de liberação / bloqueios:** V05; contrato de accepted/rejected/unknown preservado desde o primeiro envio.

### Source IDs e contexto mínimo

**PRD:** US-24; US-25; RN-07; RN-09; RN-12; C24; C25; C36.

**SPEC:** REQ-007; REQ-009; REQ-012; DLY-001; DLY-005; DLY-007; DLY-009; AC-009; FT-03; FT-05.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9, 12.4–12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.2–4.3, 4.9–4.10 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Claim → modo humano → comando de mensagem → intenção/outbox → dispatcher → canal simulado → estado web; incluir correlação mínima e incidente de envio incerto.

### Fora de escopo

Canal real e promessa de entrega externa exatamente uma vez.

### Acceptance Criteria

- [ ] Duas assunções concorrentes produzem um responsável atual; atribuição isolada não significa assunção.
- [ ] Mensagem manual identifica autor; 202 permanece pendente até resultado conclusivo e aceitação não é leitura.
- [ ] Timeout após possível aceitação fica unknown e não é reenviado; erro comprovadamente rejeitado permanece distinguível.
- [ ] Somente uma tentativa por conversa é autorizada; texto respeita limite do canal sem truncar condições comerciais.

### Testes / verificação

Seams propostas: claim/messages, consulta de conversa e saída do adaptador. FT-03/FT-05, C25/C36; caso-base manual de C24.

### Handoff

Contrato do sender, estados de entrega, barreiras de concorrência controláveis e tratamento mínimo de unknown.

<a id="sl-07"></a>

## SL-07 — Aplicar pausa e prioridade humana na fronteira de envio

**Resultado esperado:** Gestor controla automação e compreende quando um envio anterior ainda está em verificação.

**Depende de:** [SL-02](#sl-02), [SL-06](#sl-06).

**Condições de liberação / bloqueios:** T01 para apresentação/aceite de controle aplicado com tentativa externa pendente.

### Source IDs e contexto mínimo

**PRD:** US-13; US-24; RN-02; RN-09; C24; C26; C27; C45.

**SPEC:** REQ-009; AC-009; DLY-002; DLY-003; DLY-004; T01; FT-04.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9–10, 12.4 → obrigações/contratos da [SPEC](spec-v1.md) §§4.9–4.10, 9.2 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Pausa global, claim e retorno explícito → estado/epochs → autorização serializada do sender → resultado na UI. Usar intenções automáticas sintéticas para exercitar a corrida antes da IA real.

### Fora de escopo

Ativação incompleta real e agendas de follow-up ainda não implementadas.

### Acceptance Criteria

- [ ] Restrição confirmada antes da autorização impede a saída; tentativas em curso retornam controle aplicado e conclusão pendente.
- [ ] Reativação global preserva modo humano e bloqueios individuais; resume-ai exige pessoa autorizada e elegibilidade atual.
- [ ] Pausa não apaga histórico nem impede mensagem manual legítima; retorno à IA não reabre intenções canceladas.
- [ ] Os dois lados da fronteira de envio ficam demonstrados, sem declarar cancelamento de operação possivelmente aceita.

### Testes / verificação

Seams propostas: comandos de controle e sender observado no canal simulado. FT-04 em cada barreira; C24/C26/C27/C45, com restrição de contato sintética até SL-08.

### Handoff

Semântica aprovada de T01, ordem de autorização e evidências que a IA/follow-up deverão preservar.

<a id="sl-08"></a>

## SL-08 — Persistir opt-out e encaminhar novo contato bloqueado

**Resultado esperado:** Pedido de parar impede novas saídas automáticas e continua visível quando o contato volta.

**Depende de:** [SL-07](#sl-07).

**Condições de liberação / bloqueios:** V04 para reautorização e eventual confirmação única; até aprovação, confirmação automática desabilitada.

### Source IDs e contexto mínimo

**PRD:** US-22; RN-11; C27; C41; V04.

**SPEC:** REQ-011; AC-011; AUT-006; CON-005.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9–10, 12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.6, 4.9, 4.11 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Entrada de interrupção → preferência durável com origem → invalidação de intenções → visibilidade à equipe; nova mensagem fica no histórico sem remover bloqueio.

### Fora de escopo

Inventar autorização por silêncio ou liberar confirmação única sem V04.

### Acceptance Criteria

- [ ] Pedido inequívoco persiste o bloqueio por empresa/canal/contato antes de nova autorização de envio.
- [ ] Nova mensagem, retry e reativação global não removem opt-out nem ressuscitam intenções antigas.
- [ ] Equipe vê motivo e contexto; eventual reautorização exige evidência e comando aprovado, nunca inferência pelo contato novo.

### Testes / verificação

Seams propostas: inbound, preferências observáveis na conversa e sender. C27/C41, reinício e opt-out concorrente com tentativa externa segundo T01.

### Handoff

Restrição reutilizável e política de reautorização pendente/aprovada para SL-23.

<a id="sl-09"></a>

## SL-09 — Recuperar trabalho interrompido sem repetir envio incerto

**Resultado esperado:** Após queda de worker/broker, trabalho válido retoma e incertezas permanecem tratáveis pelo gestor.

**Depende de:** [SL-08](#sl-08).

**Condições de liberação / bloqueios:** Parâmetros técnicos documentados e testáveis; nenhuma dependência de IA real.

### Source IDs e contexto mínimo

**PRD:** US-32; RN-12; C35; C36; C38.

**SPEC:** REQ-012; AC-012; OPS-002; OPS-003; OPS-004; OPS-006; OPS-008; DLY-006; FT-01; FT-08; FT-11; VAL-004.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§7/J05, 9, 12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.9, 4.12, 6.2 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Watchdog lê registros duráveis → recupera tarefa elegível ou incidente → operador acompanha motivo, dono e próxima ação. Exercitar leases/fencing no caminho já entregue.

### Fora de escopo

Recuperação por apagar histórico e garantia não oferecida pelo provedor.

### Acceptance Criteria

- [ ] Perda do Redis reconstrói trabalho a partir do banco; commit seguido de queda antes do ack não duplica efeito.
- [ ] Executor vencido não aplica decisão; dispatching abandonado torna-se unknown, salvo prova de ausência da chamada.
- [ ] Retries seguros são limitados, respeitam prazo/Retry-After e terminam em incidente; unknown não é reenviado automaticamente.
- [ ] Falha de uma conversa não bloqueia as demais; resolução não transforma incerteza em sucesso sem evidência.

### Testes / verificação

Seams propostas: operação de recuperação/incidentes e efeitos na conversa/canal. FT-01/FT-08/FT-11, C35/C36/C38; banco/broker reais.

### Handoff

Procedimentos reproduzíveis de crash/reinício, estados de incidente e limites registrados.

<a id="sl-10"></a>

## SL-10 — Manter catálogo comercial versionado

**Resultado esperado:** Gestor cadastra, corrige e consulta produto/preço/disponibilidade da sua empresa.

**Depende de:** [SL-02](#sl-02).

**Condições de liberação / bloqueios:** Para D0, catálogo estruturado é a única fonte comercial e dados são sintéticos; V09 integral continua aberta para múltiplas fontes. Catálogo ainda não comprova resposta comercial.

### Source IDs e contexto mínimo

**PRD:** US-07; RN-04; C10; C12; V09.

**SPEC:** REQ-004; AC-004; DAT-001; DAT-005.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §9, §12.3 → obrigações/contratos da [SPEC](spec-v1.md) §§4.1, 4.3, 4.8 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Formulário → validação monetária/versionamento → catálogo persistido → leitura autorizada, preparando a fonte estruturada para atendimento.

### Fora de escopo

Descontos arbitrários, estoque/ERP e resposta de IA.

### Acceptance Criteria

- [ ] Preço zero é válido, desconhecido permanece null e valor decimal não perde precisão.
- [ ] Disponibilidade e revisão comercial persistem; correção não reescreve histórico de referências anteriores.
- [ ] Escrita exige gestor; produto de Beta não aparece em Alfa; conflito de edição não confirma atualização.

### Testes / verificação

Seams propostas: products e formulário. CRUD versionado, preço zero/desconhecido e autorização; C10/C12 somente quanto à origem dos dados, completados em SL-12/SL-13.

### Handoff

Contrato de catálogo e revisão comercial com fixtures rastreáveis.

<a id="sl-d01"></a>

## SL-D01 — Responder sobre o catálogo com OpenAI no canal de teste

**Resultado esperado:** Uma pergunta sobre produto sintético recebe resposta fundamentada no catálogo da empresa, ou encaminhamento quando falta suporte, com histórico observável.

**Depende de:** [SL-05](#sl-05), [SL-09](#sl-09), [SL-10](#sl-10).

**Condições de liberação / bloqueios:** Modelo específico da API da OpenAI, credencial, orçamento e massa sintética definidos; catálogo é a única fonte comercial de D0. Confirmar seams antes de escrever testes.

### Source IDs e contexto mínimo

**PRD:** US-14; US-15; US-19; RN-04; RN-05; RN-13; C08; C10; C20; C21; C44; V09.

**SPEC:** REQ-004; REQ-005; REQ-008; REQ-013; AC-004; AI-001; AI-003; CON-002; SEC-007; FT-12; FT-15.

**Relação de contexto:** [PRD](PRD-v1.md) §5/D0, §§7/J02, 9 e 12.3 → [SPEC](spec-v1.md) §1.4 e §§4.7–4.9 → este slice. Cobertura D0 parcial; não substitui [SL-12](#sl-12) nem [SL-18](#sl-18).

### Escopo

Entrada do canal de teste já entregue → leitura autorizada do catálogo/revisão → chamada controlada à API da OpenAI → validação dos fatos comerciais e limites → intenção de resposta pelo sender existente ou encaminhamento humano → histórico. Registrar modelo/prompt/parâmetros e custo conhecido sem segredos. Usar IDs duráveis e controles de pausa, opt-out e `unknown` existentes.

### Fora de escopo

Documentos/vetores, rubrica de qualificação, score, follow-up e avaliação ampla de qualidade de M1. Não transformar texto do modelo em permissão de ferramenta ou preço sem validação.

### Acceptance Criteria

- [ ] Produto disponível recebe resposta coerente com nome, preço conhecido e disponibilidade persistidos; zero é preço válido e desconhecido não é inventado.
- [ ] Produto ausente/indisponível, fonte conflitante, pedido de desconto não autorizado e instrução maliciosa não produzem afirmação ou ação proibida; lead encontra caminho humano.
- [ ] Falha, timeout, resposta inválida e limite da OpenAI têm saída tratável e finita; segredo e conteúdo pessoal não aparecem em logs/DTOs.
- [ ] Reentrega da mesma entrada não cria segunda intenção/efeito; Alfa não usa catálogo da Beta; versão do modelo e casos de referência sintéticos ficam registrados.

### Testes / verificação

Seams propostas: entrada/sender de teste, consulta de conversa e LLMProvider externo; PostgreSQL/Redis locais, OpenAI real em contas de teste, falhas controladas e dois tenants. A avaliação deste roteiro não aprova SL-18.

### Handoff

Contrato do adaptador OpenAI, configuração sem segredos, conjunto mínimo de perguntas, resultados e limites para a integração Telegram.

<a id="sl-d02"></a>

## SL-D02 — Vincular no app um bot Telegram preexistente

**Resultado esperado:** Gestor informa no aplicativo a credencial de um bot que criou antes, vê vínculo e estado reais e consegue corrigir uma falha sem duplicar canal.

**Depende de:** [SL-02](#sl-02), [SL-04](#sl-04), [SL-09](#sl-09).

**Condições de liberação / bloqueios:** Bot de teste criado pelo usuário; credencial fornecida por canal seguro, configuração de segredo e endpoint HTTPS alcançável autorizados. V01 permanece aberta para self-service completo.

### Source IDs e contexto mínimo

**PRD:** US-10; RN-03; C01; C04; V01.

**SPEC:** REQ-003; AC-003; SEC-004; SEC-005; EXT-001.

**Relação de contexto:** [PRD](PRD-v1.md) §5/D0, §§9, 12.2 e 14/V01 → [SPEC](spec-v1.md) §1.4 e §§4.2–4.3 → este slice. C01/C04 apenas parciais, pois a criação externa do bot não é self-service.

### Escopo

Formulário de vínculo → verificação da identidade do bot → armazenamento protegido do token fora do código → associação exclusiva à organização → configuração/estado do webhook e ação de retomada. Vínculo pendente não aparece conectado.

### Fora de escopo

Criar bot pelo app, automatizar BotFather, declarar V01 resolvida para M1, WhatsApp e credenciais de produção.

### Acceptance Criteria

- [ ] Somente gestor vincula bot de teste; token não aparece novamente em resposta, histórico, logs, repositório ou outra organização.
- [ ] Identidade e estado do bot são verificados no provedor; token inválido/duplicado ou webhook indisponível geram estado e correção explícitos, sem falsa conexão.
- [ ] Repetir a operação não cria segundo vínculo; webhook autentica origem e resolve a organização pelo vínculo confiável, não pelo corpo recebido.

### Testes / verificação

Seams propostas: formulário/status, operação de vínculo e webhook Telegram; testes negativos de credencial, tenant e duplicata, mais bot real controlado. Sanitizar evidências e registrar a capacidade efetivamente observada.

### Handoff

Bot de teste vinculado, configuração do endpoint, estado de webhook e procedimento de recuperação; V01/C01/C04 continuam parciais.

<a id="sl-d03"></a>

## SL-D03 — Demonstrar atendimento Telegram ponta a ponta

**Resultado esperado:** Gestor cria conta, cadastra produtos, vincula o bot e observa uma primeira conversa real com resposta apoiada no catálogo e histórico no aplicativo.

**Depende de:** [SL-08](#sl-08), [SL-D01](#sl-d01), [SL-D02](#sl-d02).

**Condições de liberação / bloqueios:** Modelo/credencial/orçamento e bot/HTTPS de teste operacionais; configuração mínima de ativação D0 explícita, sem promover checklist incompleto a M1.

### Source IDs e contexto mínimo

**PRD:** US-12; US-13; US-14; RN-02; RN-03; RN-04; C01; C03; C08; C10; C44; V02.

**SPEC:** REQ-002; REQ-003; REQ-004; REQ-005; AC-002; SEC-005; EXT-001; VAL-004; VAL-005.

**Relação de contexto:** [PRD](PRD-v1.md) §5/D0, §§7/J01–J02 e 12.2–12.3 → [SPEC](spec-v1.md) §1.4 e §§4.2–4.3, 4.6, 4.9 → este slice. D0 não encerra [SL-21](#sl-21) ou M1.

### Escopo

Ativação D0 explícita → webhook Telegram autenticado/normalizado → fluxo de catálogo/OpenAI de SL-D01 → sender Telegram com resultado real → histórico/estado no app. Exercitar pergunta suportada, ausente e pedido humano, reentrega e falha/incerteza do envio em contas de teste.

### Fora de escopo

Qualificação, documentos, follow-up, WhatsApp, piloto e avaliação ampla do modelo. Nenhuma resposta automática antes da ativação.

### Acceptance Criteria

- [ ] Jornada D0 do PRD passa de conta criada a resposta no Telegram e histórico visível, com produtos sintéticos cadastrados pelo gestor no app.
- [ ] Pergunta sem suporte e pedido humano não fabricam informação; pausa/opt-out e `unknown` impedem continuação ou retry indevido.
- [ ] Webhook inválido/eco não aciona o agente; reentrega não duplica; Alfa/Beta permanecem isoladas, inclusive nos produtos e no vínculo do bot.
- [ ] Evidência registra modelo, revisão de catálogo, configuração de teste, esperado/observado e custos conhecidos; limitações C01/V01 e pendências M1/M2 permanecem explícitas.

### Testes / verificação

E2E web + bot Telegram e OpenAI reais em ambiente controlado, com dados sintéticos; PostgreSQL/Redis e falhas de canal. Registrar `passed`, `failed`, `blocked` ou `not_run` por critério. A repetição de uma única conversa não prova qualidade geral do modelo.

### Handoff

Roteiro reproduzível da apresentação, evidências D0, configuração sem segredos e lacunas preservadas para SL-11–SL-25.

<a id="sl-11"></a>

## SL-11 — Disponibilizar documento com estado e recuperação de falha

**Resultado esperado:** Gestor envia documento e sabe quando pode ser usado ou como corrigir uma falha.

**Depende de:** [SL-10](#sl-10).

**Condições de liberação / bloqueios:** V06 para formatos/tamanhos; perfil de embeddings e provedor fixados conforme SPEC, sujeitos à aprovação de dependências/custo.

### Source IDs e contexto mínimo

**PRD:** US-05; US-06; RN-04; C11; V06.

**SPEC:** REQ-004; AC-004; SEC-006; DAT-003; DAT-005; FT-10.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §9, §12.3 → obrigações/contratos da [SPEC](spec-v1.md) §§4.3, 4.5, 4.8 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Upload privado → validação/extração isolada → indexação por versão → estado no aplicativo e consulta autorizada de evidências. Expandir por formato aprovado em ciclos pequenos.

### Fora de escopo

OCR, páginas externas e formatos não aprovados.

### Acceptance Criteria

- [ ] Somente versão inteiramente pronta é utilizável; falha fica acionável e não remove fontes válidas independentes.
- [ ] Tipo real/tamanho e conteúdo ativo são tratados conforme política; extração não executa conteúdo nem acessa rede.
- [ ] Reenvio do mesmo conteúdo/perfil não duplica ingestão; localização e versão da evidência ficam recuperáveis.
- [ ] Alfa não baixa arquivos nem recupera vetores da Beta; dimensão/perfil e filtro de tenant são consistentes.

### Testes / verificação

Seams propostas: uploads/submit/status e KnowledgeRepository/download autorizado. C11/FT-10; arquivos sintéticos válidos, inválidos e maliciosos, um formato por ciclo.

### Handoff

Estados de ingestão, perfil/versões, fontes utilizáveis e rejeições comprovadas para SL-12.

<a id="sl-12"></a>

## SL-12 — Responder com fonte válida ou encaminhar a dúvida

**Resultado esperado:** Lead obtém resposta sustentada no catálogo/trecho da empresa ou vê a solicitação chegar à equipe.

**Depende de:** [SL-11](#sl-11), [SL-D01](#sl-d01).

**Condições de liberação / bloqueios:** V09 e política comercial aplicável; primeiro ciclo usa LLMProvider fake. Modelo real somente após controles e SL-18.

### Source IDs e contexto mínimo

**PRD:** US-14; US-15; US-19; RN-04; RN-05; RN-13; C08; C09; C10; C20; C21; C44; C46; V09.

**SPEC:** REQ-004; REQ-005; REQ-008; REQ-013; AC-004; AC-013; AI-001; AI-003; AI-004; CON-002; SEC-007; FT-12; FT-15.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§7/J02, 9, 12.3–12.4 → obrigações/contratos da [SPEC](spec-v1.md) §§4.7–4.10, 6.3 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Mensagem → snapshot controlado → recuperação → plano tipado → validação de evidência/permissão → intenção e sender ou handoff → histórico. Implementar pergunta sustentada primeiro, depois cada recusa.

### Fora de escopo

Score, fechamento autônomo e prometer qualidade do modelo real a partir de fake.

### Acceptance Criteria

- [ ] Preço/disponibilidade vêm de dados validados; produto indisponível não é oferecido como comprável.
- [ ] Fonte ausente, conflitante ou inacessível produz abstenção/encaminhamento com contexto, sem afirmação inventada.
- [ ] Pedido de exceção, assunto sensível e instruções maliciosas não autorizam ferramenta, desconto ou acesso proibidos.
- [ ] Limites de execução/saída e falhas do provedor geram tratamento finito; apresentação identifica automação e caminho para humano sem expor segredos.

### Testes / verificação

Seams propostas: entrada→saída do atendimento e CRM; LLMProvider como fronteira externa fake. C08/C09/C10/C20/C21/C44/C46; FT-12/FT-15 por variante. Não exigir redação idêntica.

### Handoff

Plano tipado, evidências rastreáveis, casos de referência e regras de abstenção para avaliação real.

<a id="sl-13"></a>

## SL-13 — Invalidar fonte e preparação de resposta antiga

**Resultado esperado:** Gestor substitui/revoga informação e respostas ainda não autorizadas deixam de usar a versão antiga.

**Depende de:** [SL-12](#sl-12).

**Condições de liberação / bloqueios:** V09/T01; sender e revisão comercial já exercitados.

### Source IDs e contexto mínimo

**PRD:** US-05; RN-02; RN-04; C12; V09.

**SPEC:** REQ-004; AC-004; DLY-008; DLY-003; AI-007; FT-06; FT-14; T01.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §9, §12.3 → obrigações/contratos da [SPEC](spec-v1.md) §§4.8–4.9, 9.3 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Alteração na UI → revogação/revisão → recuperação restrita → revalidação e regeneração da mesma intenção antes do envio.

### Fora de escopo

Apagar histórico e resolver conflito comercial sem política aprovada.

### Acceptance Criteria

- [ ] Fonte invalidada não é recuperada mesmo se substituição ainda processa; histórico de resposta anterior continua preservado.
- [ ] Preparação antiga sem tentativa externa é substituída na mesma causa lógica; job antigo não envia a versão superada.
- [ ] Accepted/unknown/cancelled/expired não são reabertos por regeneração.
- [ ] Alteração durante tentativa externa mantém conclusão pendente conforme T01 e não promete recolher mensagem.

### Testes / verificação

Seams propostas: produtos/conhecimento, fluxo de atendimento e saída do adaptador. C12/FT-06 e ramo de revogação de FT-14 nas barreiras de geração/autorização/HTTP.

### Handoff

Revisões e casos de corrida comercial; demais exclusões de dados ficam para SL-32.

<a id="sl-14"></a>

## SL-14 — Coletar fatos, receber mídia e preservar correções

**Resultado esperado:** Conversa mantém necessidade atual, distingue recusa de ausência e oferece continuidade após mídia não interpretada.

**Depende de:** [SL-12](#sl-12).

**Condições de liberação / bloqueios:** V06 para mídia suportada; texto obrigatório e saída explícita para não suportada.

### Source IDs e contexto mínimo

**PRD:** US-16; US-17; US-18; US-20; RN-05; C13; C14; C17; C18; C19; C43.

**SPEC:** REQ-005; AC-005; AI-005; AI-006; AI-007; CON-005; FT-11.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9–10, 12.3, 12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.6–4.7, 9.5 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Entrada → extração de fatos com origem/ordem → CAS de estado → histórico/CRM → próxima resposta contextual; retomada do grafo revalida causa e restrições.

### Fora de escopo

Compreensão de áudio/imagem e fusão automática de identidades.

### Acceptance Criteria

- [ ] Telefone/orçamento desconhecidos ou recusados não são fabricados; coleta não bloqueia pedido humano.
- [ ] Correção válida atualiza o fato e preserva origem/histórico; mensagem atrasada não restaura dado antigo.
- [ ] Ordem ambígua fica pendente de revisão; execução/checkpoint obsoleto não aplica efeitos.
- [ ] Mídia não suportada oferece texto/humano sem inventar conteúdo; retorno ao mesmo contato conserva contexto.

### Testes / verificação

Seams propostas: conversa inbound/outbound e leitura de fatos/CRM. C13/C14/C17/C18/C19/C43 e FT-11 na retomada de IA.

### Handoff

Proveniência de fatos, recusas e fixtures de ordem/retomada para qualificação.

<a id="sl-15"></a>

## SL-15 — Configurar rubrica e qualificar com evidências

**Resultado esperado:** Gestor configura critérios e observa classificação justificada; lead quente é encaminhado.

**Depende de:** [SL-14](#sl-14).

**Condições de liberação / bloqueios:** V03: rubrica/categorias/evidências aprovadas; não inventar score numérico.

### Source IDs e contexto mínimo

**PRD:** US-08; US-35; RN-06; RN-08; C15; C16; C21; V03.

**SPEC:** REQ-006; REQ-008; AC-006; AI-002.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §9, §12.3 → obrigações/contratos da [SPEC](spec-v1.md) §§4.7, 4.10, 6.3 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Rubrica versionada no aplicativo → evidências extraídas → avaliador determinístico → classificação/lacunas no CRM → handoff quando devido.

### Fora de escopo

Metodologia comercial universal, pesos e limiares não definidos.

### Acceptance Criteria

- [ ] Mesmos fatos e rubrica produzem categoria e razões reproduzíveis; faltas/recusas continuam explícitas.
- [ ] Entusiasmo sem evidência suficiente não produz quente.
- [ ] Quente fundamentado dispara encaminhamento com motivo; pedido humano permanece independente de score.
- [ ] Alteração confirmada de rubrica rege novas decisões sem apagar avaliações históricas.

### Testes / verificação

Seams propostas: configuração de rubrica e atendimento/CRM; C15/C16 e gatilho quente de C21, com resultados esperados derivados da rubrica aprovada.

### Handoff

Rubrica versionada, casos conhecidos e explicações para revisão humana/multicanal.

<a id="sl-16"></a>

## SL-16 — Corrigir classificação e concluir oportunidade por pessoa

**Resultado esperado:** Pessoa corrige avaliação ou registra resultado comercial sem sobrescrita tardia da IA.

**Depende de:** [SL-07](#sl-07), [SL-15](#sl-15).

**Condições de liberação / bloqueios:** Permissões V05; transições propostas aprovadas.

### Source IDs e contexto mínimo

**PRD:** US-26; US-27; US-33; RN-06; RN-07; RN-09; RN-13; C28; C29; C30; C37.

**SPEC:** REQ-006; REQ-007; AC-006; AC-007; CON-007; FT-07.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9–10, 12.4–12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.3, 4.7, 4.10 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Comandos web de classificação/estágio → versão, motivo e auditoria atômicos → leitura CRM; nova mensagem após terminal segue para revisão.

### Fora de escopo

Automação de fechamento e alteração silenciosa da revisão humana.

### Acceptance Criteria

- [ ] Correção humana exige motivo e permanece protegida contra saída antiga do modelo.
- [ ] Ganho/perda/reabertura exigem humano autorizado; intenção de compra não marca ganho.
- [ ] Nova mensagem em oportunidade encerrada fica visível sem reabrir nem automatizar acompanhamento.
- [ ] Falha de persistência não confirma alteração; estado anterior permanece acessível e pendência orienta tratamento.

### Testes / verificação

Seams propostas: qualification/stage e atendimento. C28/C29/C30/C37, FT-07 e rollback observado pela API.

### Handoff

Transições, proteção humana e fixtures terminais para cancelamento de follow-up.

<a id="sl-17"></a>

## SL-17 — Consultar CRM, resumo e redistribuir responsabilidade

**Resultado esperado:** Gestor encontra oportunidade por estágio/classificação/responsável e redistribui sem perder contexto.

**Depende de:** [SL-03](#sl-03), [SL-16](#sl-16).

**Condições de liberação / bloqueios:** V05 para redistribuição/atribuição; projeções respeitam autorização existente.

### Source IDs e contexto mínimo

**PRD:** US-23; US-28; US-29; US-30; RN-07; RN-08; RN-09; C02; C23; C42.

**SPEC:** REQ-001; REQ-007; REQ-008; AC-001; AC-008; AI-005.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §9, §12.4–12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§3.5, 4.3–4.4, 4.7, 4.10 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Lista filtrada/paginada → conversa/histórico/resumo → atribuição auditada → visão atualizada de gestor/vendedor. Resumo incorpora fatos, dúvidas e próximo passo.

### Fora de escopo

Analytics avançado e atualização otimista de controles críticos.

### Acceptance Criteria

- [ ] Filtros incluem sem responsável; lista e cursor não ampliam acesso de vendedor ou outra empresa.
- [ ] Resumo informa até onde cobre o histórico; falha não impede acesso às mensagens nem assunção.
- [ ] Redistribuição usa vendedor elegível, registra motivo e preserva modo humano/aguardando.
- [ ] Estado confirmado vem do servidor; erro, vazio, pendência e conflito têm tratamento distinto na UI.

### Testes / verificação

Seams propostas: leads/conversations/assign e telas. C02/C23/C42, dois vendedores e paginação; resumo com correção posterior.

### Handoff

Projeções e permissões do CRM, continuidade de resumo e procedimento de fila sem responsável.

<a id="sl-18"></a>

## SL-18 — Validar atendimento com modelo real versionado

**Resultado esperado:** Atendimento protegido demonstra decisões/evidências corretas com o modelo escolhido e não apenas com fake.

**Depende de:** [SL-13](#sl-13), [SL-15](#sl-15), [SL-17](#sl-17), [SL-D01](#sl-d01).

**Condições de liberação / bloqueios:** Modelo/provedor, acesso e orçamento aprovados; V03/V09 para referências comerciais. Sem dados reais.

### Source IDs e contexto mínimo

**PRD:** US-14; US-15; US-35; OBJ-03; OBJ-07; RN-13; C20; C40; C46.

**SPEC:** REQ-013; AI-008; EXT-003; FT-12; FT-15; VAL-006.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9, 12.3, 13.2 → obrigações/contratos da [SPEC](spec-v1.md) §§4.7, 6.2–6.4, 8.1 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Substituir somente fronteira externa de inferência; avaliar o mesmo percurso e conjunto versionado com variações de linguagem, contexto longo e falhas; registrar divergências/revisão humana.

### Fora de escopo

Roteamento multi-LLM e inferir garantia universal da suíte.

### Acceptance Criteria

- [ ] Modelo/prompt/parâmetros/fontes e resultados ficam versionados; casos críticos têm execuções repetidas.
- [ ] Todos os casos de proteção da suíte aprovada passam e divergências críticas impedem aceite.
- [ ] Avaliação considera fatos, ações e evidências, não só texto similar nem julgamento de outro LLM.
- [ ] JSON inválido, fonte inexistente e limite excedido preservam abstenção/incidente; troca de modelo/prompt exige regressão.

### Testes / verificação

Seam proposta: atendimento completo com LLMProvider real controlado; conjunto da SPEC §6.3 e FT-12/FT-15. Resultados fake e reais separados.

### Handoff

Modelo escolhido, relatório por cenário, consumo e restrições; ausência de acesso registra bloqueio, não aprovação.

<a id="sl-19"></a>

## SL-19 — Validar a experiência self-service do Telegram

**Resultado esperado:** Produto dispõe de evidência concreta para aceitar ou rejeitar o percurso de criação/vinculação do bot.

**Depende de:** [SL-00](#sl-00).

**Condições de liberação / bloqueios:** V01 em aberto; acesso/ambiente controlado autorizado para o spike.

### Source IDs e contexto mínimo

**PRD:** US-10; RN-03; C01; C04; V01.

**SPEC:** REQ-003; EXT-001; VAL-005.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9, 14 → obrigações/contratos da [SPEC](spec-v1.md) §§1.3, 4.2, 8.1 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Spike limitado: iniciar pelo aplicativo/protótipo, confirmar propriedade, observar callback/estado e avaliar aderência ao self-service desejado; registrar decisão de V01.

### Fora de escopo

Construir alternativa de produto não aprovada e automação presumida de BotFather.

### Acceptance Criteria

- [ ] Experiência e limites reais ficam descritos com prova do vínculo seguro usuário/empresa/bot.
- [ ] Confirmação externa necessária fica explícita para decisão de Produto; não declarar viabilidade integral sem evidência.
- [ ] Token manual fica identificado como contingência de teste e não satisfaz C01/C04 finais.

### Testes / verificação

Seam proposta: ChannelProvisioner com Telegram controlado. Verificação opt-in de criação, propriedade e retomada; documentação da release/capacidade efetivamente usada.

### Handoff

Decisão de V01 e contrato comprovado para SL-20, ou bloqueio acompanhado de próxima ação.

<a id="sl-20"></a>

## SL-20 — Conectar Telegram e retomar provisionamento

**Resultado esperado:** Gestor conecta o bot pelo percurso aprovado e retoma falha sem duplicar canal.

**Depende de:** [SL-19](#sl-19), [SL-D02](#sl-d02).

**Condições de liberação / bloqueios:** V01 resolvida com experiência aprovada; credenciais e ambiente controlado autorizados.

### Source IDs e contexto mínimo

**PRD:** US-10; US-32; RN-03; C04.

**SPEC:** REQ-003; AC-003; SEC-004; EXT-001.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §9, §12.2 → obrigações/contratos da [SPEC](spec-v1.md) §§4.2–4.3, 4.12, 8.1 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

UI de conexão → operação idempotente/provisioner → vínculo seguro/credencial protegida → status/retomada web.

### Fora de escopo

Considerar conexão manual como aceite self-service.

### Acceptance Criteria

- [ ] Solicitação pendente não aparece conectada; repetir retorna operação/vínculo existente.
- [ ] Falha/expiração mostra motivo e ação de retomada; callback isolado não prova propriedade.
- [ ] Credencial não aparece em DTO/log/histórico; rotação mantém proteção e estado observável.

### Testes / verificação

Seams propostas: channels/operations e ChannelProvisioner real. C04, falha/retomada e tentativa de vínculo cruzado; sanitizar evidências.

### Handoff

Canal Telegram operacional, capacidade comprovada e procedimento de recuperação.

<a id="sl-21"></a>

## SL-21 — Ativar e atender a primeira conversa no Telegram

**Resultado esperado:** Gestor conclui prontidão e lead recebe atendimento fundamentado no Telegram com registro no aplicativo.

**Depende de:** [SL-18](#sl-18), [SL-20](#sl-20), [SL-D03](#sl-d03).

**Condições de liberação / bloqueios:** V01/V02/V03/V05/V06/V09/T01 aplicáveis resolvidas; modelo aprovado em SL-18.

### Source IDs e contexto mínimo

**PRD:** US-12; US-13; US-14; RN-02; RN-03; C01; C03; C08; C44; V02.

**SPEC:** REQ-002; REQ-005; AC-002; SEC-005; EXT-001; VAL-005.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§7/J01, 12.2–12.3, 13.1 → obrigações/contratos da [SPEC](spec-v1.md) §§4.2–4.3, 4.6, 8.1 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Checklist real → ativação explícita → webhook Telegram autenticado → núcleo existente → envio real/CRM. Adaptador não contém decisões comerciais.

### Fora de escopo

Declarar M1 concluído antes de follow-up/controle/falhas integrais.

### Acceptance Criteria

- [ ] Prontidão depende de capacidades realmente utilizáveis e responsável definido; agente inativo não atende automaticamente.
- [ ] Jornada C01 é executável sem intervenção técnica externa fora do percurso aprovado.
- [ ] Webhook inválido não processa; confirmação/eco de envio não aciona IA; IDs externos preservam identidade.
- [ ] Primeira resposta identifica automação, respeita fonte e registra aceitação real sem inferir leitura.

### Testes / verificação

Seams propostas: onboarding web e conversa Telegram controlada ponta a ponta. C01/C03/C08/C44; contrato do adaptador e negativas de autenticação.

### Handoff

Primeira jornada real e configuração de referência para follow-up e gate M1.

<a id="sl-22"></a>

## SL-22 — Configurar política e enviar um follow-up elegível

**Resultado esperado:** Gestor define política válida e observa um único acompanhamento contextual de conversa inbound sem resposta.

**Depende de:** [SL-15](#sl-15), [SL-21](#sl-21).

**Condições de liberação / bloqueios:** V04 aprovada; valores sintéticos da SPEC não são defaults comerciais.

### Source IDs e contexto mínimo

**PRD:** US-21; US-31; RN-10; C31; V04.

**SPEC:** REQ-010; AC-010; AUT-001; AUT-002; AUT-003.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§7/J03, 9, 12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.3, 4.11 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Política web → rodada após resposta aceita → próximo agendamento durável → reavaliação/geração/sender → próximo follow-up e estado no CRM.

### Fora de escopo

Prospecção fria e campanhas em massa.

### Acceptance Criteria

- [ ] Política ausente/incompleta fica desabilitada; offsets, validade, limite, janela e fuso são explícitos.
- [ ] Somente conversa iniciada pelo lead e ainda elegível recebe acompanhamento.
- [ ] No máximo o próximo ordinal é agendado; resultado incerto não cria próximo envio.
- [ ] Tarefa durável sobrevive a reinício e envio aceito fica visível com horário, sem presumir leitura.

### Testes / verificação

Seams propostas: followup-policy, Clock e atendimento/canal. C31 com tempo controlado; banco/broker reais e demonstração controlada Telegram.

### Handoff

Política versionada, causa da rodada e contrato de agenda para SL-23.

<a id="sl-23"></a>

## SL-23 — Cancelar follow-up e respeitar janela, validade e limite

**Resultado esperado:** Lead deixa de receber acompanhamento inelegível; reconexão não descarrega mensagens vencidas.

**Depende de:** [SL-16](#sl-16), [SL-22](#sl-22).

**Condições de liberação / bloqueios:** V04; controles e terminalidade já entregues.

### Source IDs e contexto mínimo

**PRD:** US-21; US-22; RN-10; RN-11; RN-12; C26; C27; C30; C32; C33; C34; V04.

**SPEC:** REQ-010; REQ-011; AC-010; AC-011; AUT-003; AUT-004; AUT-005; FT-13.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9–10, 12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.9, 4.11, 6.2 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Resposta/assunção/opt-out/encerramento/pausa/alteração de política → invalidação durável → motivo no CRM → reavaliação no instante do envio.

### Fora de escopo

Usar esperas reais de horas ou mudar limites para fazer teste passar.

### Acceptance Criteria

- [ ] Cada evento de C32 cancela agenda antiga com motivo; reativação e retorno à IA não a ressuscitam.
- [ ] Fuso, janela, meia-noite e horário de verão produzem uma ação válida dentro da expiração.
- [ ] Limite atingido vira sem resposta, nunca perda comercial automática; mudança de política não zera tentativas.
- [ ] Após indisponibilidade, expira o que venceu e libera só o próximo acompanhamento elegível; não há lote acumulado.

### Testes / verificação

Seams propostas: controles/agenda/Clock e saída observável. Todos os exemplos de C32, C33/C34/FT-13; nova resposta entre geração e autorização.

### Handoff

Evidências de cancelamento/tempo e regressões do sender para M1/M2.

<a id="sl-24"></a>

## SL-24 — Consultar operação e indicadores com custo explícito

**Resultado esperado:** Gestor identifica pendências e mede operação por canal/empresa sem exposição de segredos.

**Depende de:** [SL-17](#sl-17), [SL-23](#sl-23).

**Condições de liberação / bloqueios:** V08 para metas comerciais; métricas e amostra não implicam SLA aprovado.

### Source IDs e contexto mínimo

**PRD:** US-32; US-38; OBJ-01; OBJ-02; OBJ-03; OBJ-04; OBJ-05; OBJ-06; OBJ-07; OBJ-08; RN-15; C02; C36; C38; C44.

**SPEC:** REQ-015; AC-015; SEC-004; VAL-009.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§4, 9, 11 → obrigações/contratos da [SPEC](spec-v1.md) §§4.13, 8.4 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Completar eventos/correlação introduzidos nos percursos → agregação por janela → indicadores/incidentes no aplicativo; documentar tratamento operacional dos incidentes existentes.

### Fora de escopo

Analytics avançado, metas de piloto inventadas e conformidade jurídica declarada.

### Acceptance Criteria

- [ ] Estados, razões, dono e próxima ação ficam consultáveis; correlação liga recebimento, execução, intenção e operação.
- [ ] Indicadores separam teste de piloto, canais e janela; custo sem preço conhecido não aparece como zero.
- [ ] Latência, completude do handoff, recuperação e uso seguem definições OBJ; retorno após follow-up não vira causalidade de venda.
- [ ] Consulta e telemetria respeitam tenant/papel; logs não expõem tokens, QR ou conteúdo pessoal por padrão.

### Testes / verificação

Seams propostas: metrics/incidents e saída de telemetria sanitizada. C02/C36/C38/C44, massa com custos conhecidos/desconhecidos e resultados esperados declarados.

### Handoff

Indicadores, definições de cálculo e runbooks de canal/credencial/fila/envio incerto/documento rejeitado.

<a id="sl-25"></a>

## SL-25 — Comprovar o marco M1 no Telegram

**Resultado esperado:** Jornada Telegram possui evidências integradas de negócio, proteção e recuperação.

**Depende de:** [SL-24](#sl-24).

**Condições de liberação / bloqueios:** Todos os antecessores transitivos de SL-24 completos; decisões aplicáveis de M1 resolvidas.

### Source IDs e contexto mínimo

**PRD:** US-37; RN-14; C01; C02; C40.

**SPEC:** VAL-001; VAL-002; VAL-003; VAL-004; VAL-005; VAL-006; VAL-009; VAL-010.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§5, 12, 13 → obrigações/contratos da [SPEC](spec-v1.md) §§5–6, 10.2 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Gate de integração, sem novo pacote de funcionalidades: executar roteiro PRD §13.1 aplicável ao Telegram e reunir resultados já produzidos por cenário/versão.

### Fora de escopo

Refazer todos os testes sem causa e marcar M2 por equivalência teórica.

### Acceptance Criteria

- [ ] Todos os cenários C01–C46 aplicáveis ao Telegram passam, excluídos somente C05/C06/C39 específicos de M2.
- [ ] Alfa/Beta demonstram personalização e isolamento; gestor/vendedor demonstram encaminhamento, resposta manual e pausa sem concorrência indevida.
- [ ] Reentrega, envio incerto, falha de canal e cancelamento têm resultado observado e evidência sanitizada.
- [ ] Falha/bloqueio/não execução permanecem distintos; conclusão de M1 é parcial para o ciclo multicanal.

### Testes / verificação

Seams propostas: jornada web+Telegram real e integração controlada de falhas. Reutilizar suíte incremental; não substituir contrato real por mocks.

### Handoff

Relatório de M1, cobertura por ID, revisão e configuração replicável para M2; pendências remanescentes explícitas.

<a id="sl-26"></a>

## SL-26 — Comprovar contrato da release Evolution

**Resultado esperado:** Há evidência do contrato de conexão, entrada e resultados de envio necessário ao segundo canal.

**Depende de:** [SL-25](#sl-25).

**Condições de liberação / bloqueios:** Release, ambiente/número controlado e uso da integração autorizados; risco do canal não oficial explícito.

### Source IDs e contexto mínimo

**PRD:** US-11; RN-03; RN-12; RN-14; C05; C06; C39.

**SPEC:** REQ-003; REQ-014; EXT-002; SEC-005; COM-002.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9, 11.2, 12.2, 12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.2, 8.1, 8.4 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Spike limitado do ChannelAdapter/ChannelProvisioner contra release fixada; obter fixtures sanitizadas, autenticação efetiva, eventos e capacidades comprovadas.

### Fora de escopo

Implementar integração presumindo documentação histórica compatível.

### Acceptance Criteria

- [ ] QR/expiração, reconexão, eventos inbound, eco e confirmação são distinguíveis na release.
- [ ] Autenticação de webhook e vínculo de tenant são demonstrados; não presumir HMAC.
- [ ] Lookup/idempotência só constam como disponíveis se comprovados; incerteza externa preserva unknown.

### Testes / verificação

Seams propostas: interfaces de adaptador/provisioner com Evolution real. Provas opt-in, sem decisões comerciais específicas no adaptador.

### Handoff

Release/schema/fixtures/capacidades e limitações para SL-27/SL-28.

<a id="sl-27"></a>

## SL-27 — Conectar WhatsApp e renovar QR expirado

**Resultado esperado:** Gestor conecta WhatsApp e renova QR sem recriar empresa ou canal.

**Depende de:** [SL-26](#sl-26).

**Condições de liberação / bloqueios:** Contrato comprovado em SL-26 e operação controlada autorizada.

### Source IDs e contexto mínimo

**PRD:** US-11; RN-03; C05.

**SPEC:** REQ-003; AC-003; SEC-004; EXT-002.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §9, §12.2 → obrigações/contratos da [SPEC](spec-v1.md) §§4.2–4.3, 8.1 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

UI → operação de conexão → provisioner Evolution → confirmação/expiração → status/reconexão.

### Fora de escopo

Múltiplos números por empresa e WhatsApp oficial.

### Acceptance Criteria

- [ ] Aguardando conexão, conectado e desconectado são estados reais distintos.
- [ ] QR expirado permite novo pedido no vínculo existente; repetição não cria canais paralelos.
- [ ] QR/credenciais não vazam em logs/artefatos; callbacks não se tornam mensagens para IA.

### Testes / verificação

Seams propostas: channels/operations e tela de conexão com provedor real. C05 e idempotência de repetição.

### Handoff

Conexão controlada e evidência de recuperação do QR.

<a id="sl-28"></a>

## SL-28 — Atender no WhatsApp com o mesmo domínio

**Resultado esperado:** Contato do WhatsApp recebe atendimento e chega ao humano sem recadastrar o negócio.

**Depende de:** [SL-27](#sl-27).

**Condições de liberação / bloqueios:** SL-27 conectado; mesma configuração comercial aprovada usada no Telegram.

### Source IDs e contexto mínimo

**PRD:** US-36; RN-05; RN-12; RN-14; C08; C35; C36; C39.

**SPEC:** REQ-005; REQ-012; REQ-014; AC-012; AC-014; DLY-005; DLY-007; EXT-002.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9, 12.3–12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.2, 4.6, 4.9, 8.1 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Webhook autenticado → normalização → domínio/IA/sender existentes → resposta/handoff manual → histórico com origem WhatsApp.

### Fora de escopo

Exigir texto idêntico nos canais e inferir garantia de não bloqueio do número.

### Acceptance Criteria

- [ ] Mesmos fatos usam a mesma rubrica, catálogo e conhecimento; adaptador não implementa política comercial paralela.
- [ ] Identidade continua local ao canal, sem fundir automaticamente o contato do Telegram.
- [ ] Reentrega/eco não duplica efeitos nem aciona resposta a si mesmo; aceito/rejeitado/desconhecido mantêm semântica.
- [ ] Limite de texto do provedor não causa truncamento de condição comercial; resposta humana permanece auditada.

### Testes / verificação

Seams propostas: conversa WhatsApp real e contrato parametrizado dos adaptadores. C08/C35/C36/C39 com massa já utilizada no Telegram.

### Handoff

Evidências de atendimento/handoff no segundo canal e comparação inicial por fatos/decisões.

<a id="sl-29"></a>

## SL-29 — Recuperar WhatsApp sem interromper Telegram

**Resultado esperado:** Gestor recupera o canal indisponível enquanto o outro continua atendendo.

**Depende de:** [SL-28](#sl-28).

**Condições de liberação / bloqueios:** Ambiente com os dois canais conectados e cenários de falha controlados.

### Source IDs e contexto mínimo

**PRD:** US-11; US-32; RN-03; RN-10; RN-12; C06; C34; C38.

**SPEC:** REQ-003; REQ-010; REQ-012; OPS-005; OPS-007; AUT-005; AC-012.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§7/J05, 9, 12.2, 12.5 → obrigações/contratos da [SPEC](spec-v1.md) §§4.11–4.12 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Desconexão/falha → circuito/estado e incidente por integração → reconexão → reavaliação gradual de trabalho válido.

### Fora de escopo

Alta disponibilidade e promessa de recuperar mensagens nunca fornecidas pelo canal.

### Acceptance Criteria

- [ ] WhatsApp desconectado não aparece enviando com sucesso e não desativa atendimento elegível no Telegram.
- [ ] Reconexão conserva contexto e vínculo; follow-ups expirados não são despejados.
- [ ] Tentativas esgotadas têm dono/ação e leitura do CRM permanece disponível; filas não impedem controle/resposta humana.

### Testes / verificação

Seams propostas: reconnect/incidents e saídas dos dois canais. C06/C34/C38 com falha isolada e retorno; não confundir falta de confirmação com rejeição segura.

### Handoff

Runbook validado de desconexão/reconexão e evidência de independência operacional.

<a id="sl-30"></a>

## SL-30 — Comprovar M2 e fechar cobertura multicanal

**Resultado esperado:** Conclusão do ciclo possui evidência real nos dois canais e nas duas empresas sintéticas.

**Depende de:** [SL-29](#sl-29).

**Condições de liberação / bloqueios:** M1 evidenciado; decisões e integrações aplicáveis a M2 resolvidas.

### Source IDs e contexto mínimo

**PRD:** US-36; US-37; RN-14; C05; C06; C39; C40.

**SPEC:** REQ-014; AC-014; VAL-001; VAL-002; VAL-010.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§5, 12–13 → obrigações/contratos da [SPEC](spec-v1.md) §§5–6, 10.2 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Gate de integração: repetir jornadas relevantes e comparar decisões/evidências comerciais por canal; consolidar cenário→requisito→evidência.

### Fora de escopo

Confundir demonstração acadêmica com validação de conversão ou demanda.

### Acceptance Criteria

- [ ] C05/C06/C39 passam com integração real; demais cenários de conversa/handoff/follow-up/proteção aplicáveis são repetidos no WhatsApp.
- [ ] Fatos equivalentes produzem qualificação/gatilho equivalentes, sem recadastro; Alfa/Beta continuam isoladas.
- [ ] Cada REQ e AC aplicável tem evidência vinculada aos IDs do PRD; ausência de prova impede fechamento correspondente.
- [ ] M1 e M2 ficam separados no registro; voz permanece fora do aceite obrigatório.

### Testes / verificação

Seams propostas: roteiro multicanal PRD §13, E2E/contratos e integrações reais. Revisão de cobertura e resultados por versão.

### Handoff

Relatório M1/M2, lacunas por ID e pacote documental para preparação de piloto.

<a id="sl-31"></a>

## SL-31 — Medir carga, justiça e custo antes do piloto

**Resultado esperado:** Responsável pelo piloto consegue decidir capacidade/custo com medições declaradas.

**Depende de:** [SL-30](#sl-30).

**Condições de liberação / bloqueios:** V08 para volume/orçamento/metas reais; ambiente de carga isolado e custos autorizados.

### Source IDs e contexto mínimo

**PRD:** US-38; OBJ-02; OBJ-08; V08.

**SPEC:** REQ-015; DAT-002; DAT-004; OPS-005; VAL-008.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§4, 11, 14 → obrigações/contratos da [SPEC](spec-v1.md) §§4.13, 6.5, 8.3 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Executar perfil sintético da SPEC §6.5 sobre jornadas existentes → drenar filas → registrar latência, duplicação, isolamento, conexões e consumo → validar capacidade proposta.

### Fora de escopo

Otimização prematura, HNSW sem medição e infraestrutura de alta disponibilidade.

### Acceptance Criteria

- [ ] Perfil, infraestrutura, amostra, históricos e latências externas simuladas ficam registrados.
- [ ] Proteções de isolamento/idempotência persistem sob rajada; atendimento humano/tenant menor não fica bloqueado pela ingestão ou outro tenant.
- [ ] Limites medidos são comparados às metas de laboratório propostas, sem promovê-las a SLA.
- [ ] Volume, orçamento e critérios de continuidade do piloto só ficam aprovados mediante V08; custo desconhecido continua explícito.

### Testes / verificação

Seams propostas: API/webhooks, fila e métricas com k6/provedores simulados; medir consultas/conexões quando houver gargalo observado.

### Handoff

Relatório de carga/custo, parâmetros operacionais e decisão V08 ou bloqueio para piloto.

<a id="sl-32"></a>

## SL-32 — Aplicar política de dados e exclusão com jobs pendentes

**Resultado esperado:** Pedido autorizado de exclusão/revogação tem tratamento coerente sem reintrodução por trabalho antigo.

**Depende de:** [SL-30](#sl-30).

**Condições de liberação / bloqueios:** V07 aprovada antes de qualquer piloto com dados reais.

### Source IDs e contexto mínimo

**PRD:** RN-01; RN-15; V07.

**SPEC:** SEC-008; COM-001; FT-14; VAL-009.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9, 14 → obrigações/contratos da [SPEC](spec-v1.md) §§4.13, 8.4 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Solicitação conforme política → bloquear novos jobs/envios → revogar fontes → tratar textos, arquivos, vetores, checkpoints, caches e retenção de backups → verificação documentada.

### Fora de escopo

Criar política legal por suposição e usar dados reais para teste.

### Acceptance Criteria

- [ ] Bloqueio antecede limpeza; job já enfileirado não restaura dado nem envia conteúdo revogado.
- [ ] Retenção/exclusão cobre todos os suportes e acessos; tombstones só persistem conforme justificativa aprovada.
- [ ] Aviso, finalidade, responsáveis e tratamento de pedidos refletem V07, sem declarar conformidade jurídica por execução técnica.

### Testes / verificação

Seams propostas: procedimento autorizado de exclusão e consultas/recuperação/atendimento subsequentes; FT-14 completo com massa sintética, sem consultas laterais como substituto de resultado público.

### Handoff

Política versionada, evidência de exclusão e bloqueios a reaplicar no restore.

<a id="sl-33"></a>

## SL-33 — Restaurar operação com automação inicialmente bloqueada

**Resultado esperado:** Operação restaurada preserva restrições e não repete saídas antigas ao voltar.

**Depende de:** [SL-31](#sl-31), [SL-32](#sl-32).

**Condições de liberação / bloqueios:** V07/V08 para retenção/RPO/RTO; ambiente e operações de backup/restore autorizados.

### Source IDs e contexto mínimo

**PRD:** RN-12; RN-15; OBJ-05; V07; V08.

**SPEC:** INF-004; VAL-007; SEC-008; CON-005.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§9, 11, 14 → obrigações/contratos da [SPEC](spec-v1.md) §§4.13, 8.2–8.3 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Backup de dados/arquivos → restore isolado com automação desabilitada → reaplicar bloqueios/exclusões posteriores → reconciliar trabalho → validar retorno seguro.

### Fora de escopo

Restore sobre produção sem autorização e promessa de RPO/RTO não medidos.

### Acceptance Criteria

- [ ] Ensaio recupera banco/arquivos e declara ponto de recuperação, perdas e duração observados.
- [ ] Opt-out, controle humano, exclusões e incertezas são reconciliados antes de liberar automação.
- [ ] Instalação/upgrade e rollback operacional por compatibilidade têm procedimento verificado; migration aplicada não é reescrita.
- [ ] Histórico/identidades deduplicadas continuam coerentes e nenhuma intenção desconhecida vira retry cego.

### Testes / verificação

Seams propostas: runbook de restore e leituras/controles/envios após restauração; banco/storage reais isolados, incluindo restrição posterior ao backup.

### Handoff

Runbook de restore com evidência, compatibilidade de migrations e limitações observadas.

<a id="sl-34"></a>

## SL-34 — Revisar prontidão documental e operacional do piloto

**Resultado esperado:** Há um pacote auditável para decidir o início do piloto, sem confundir planejamento com execução.

**Depende de:** [SL-33](#sl-33).

**Condições de liberação / bloqueios:** M1/M2 comprovados, V07/V08 resolvidas e demais decisões aplicáveis aprovadas.

### Source IDs e contexto mínimo

**PRD:** US-38; OBJ-01; OBJ-02; OBJ-03; OBJ-04; OBJ-05; OBJ-06; OBJ-07; OBJ-08; V07; V08.

**SPEC:** VAL-001; VAL-002; VAL-003; VAL-004; VAL-005; VAL-006; VAL-007; VAL-008; VAL-009; VAL-010.

**Relação de contexto:** resultado e cenários do [PRD](PRD-v1.md) §§4, 13.2, 14 → obrigações/contratos da [SPEC](spec-v1.md) §§4.13, 10.2 → este slice. Carregar apenas esses trechos, os IDs acima e os handoffs diretos. 

### Escopo

Revisar evidências vigentes, runbooks, políticas, amostra/metas/custo e mapa de impacto; produzir handoff para a decisão de piloto.

### Fora de escopo

Executar deploy, contactar usuários ou ampliar para voz/WhatsApp oficial.

### Acceptance Criteria

- [ ] Requisitos, cenários e falhas obrigatórias têm cobertura executada ou bloqueio explícito; nenhuma pendência crítica é ocultada por resumo.
- [ ] Runbooks de Redis, canal, credencial, fila humana, unknown, documento rejeitado e restore indicam diagnóstico, ação e retorno seguro.
- [ ] Fonte/modelo/configuração/revisão de cada evidência estão identificados; mudança relevante invalida/requer revisão dos resultados afetados.
- [ ] Início/publicação/deploy do piloto depende da autorização correspondente; este gate não afirma que piloto ou ganho de negócio ocorreram.

### Testes / verificação

Fronteira documental/operacional: revisar VAL-001 a VAL-010 e PRD §13.2; repetir execução somente por mudança, falha ou lacuna justificada.

### Handoff

Decisão de prontidão, bloqueios remanescentes, responsável e próxima ação mínima no harness.

## Cobertura navegável e fechamento

O vínculo listado abaixo é **planejado**. Presença de um ID não comprova implementação nem aceite integral: requisitos compartilhados precisam das evidências de todos os seus percursos. No harness, cada relação deve chegar ao critério do slice, contrato e artefato de verificação correspondente. Critérios locais não recebem IDs de requisito fictícios.

### Requisitos técnicos e regras de negócio

| PRD | SPEC | Slices com contribuição direta |
| --- | --- | --- |
| PRD: RN-01 | SPEC: REQ-001 | SL-01, SL-03, SL-17 |
| PRD: RN-02 | SPEC: REQ-002 | SL-02, SL-D03, SL-21 |
| PRD: RN-03 | SPEC: REQ-003 | SL-D02, SL-D03, SL-19, SL-20, SL-26, SL-27, SL-29 |
| PRD: RN-04 | SPEC: REQ-004 | SL-10, SL-D01, SL-D03, SL-11, SL-12, SL-13 |
| PRD: RN-05 | SPEC: REQ-005 | SL-04, SL-D01, SL-D03, SL-12, SL-14, SL-21, SL-28 |
| PRD: RN-06 | SPEC: REQ-006 | SL-15, SL-16 |
| PRD: RN-07 | SPEC: REQ-007 | SL-04, SL-06, SL-16, SL-17 |
| PRD: RN-08 | SPEC: REQ-008 | SL-03, SL-05, SL-12, SL-15, SL-17 |
| PRD: RN-09 | SPEC: REQ-009 | SL-06, SL-07 |
| PRD: RN-10 | SPEC: REQ-010 | SL-22, SL-23, SL-29 |
| PRD: RN-11 | SPEC: REQ-011 | SL-08, SL-23 |
| PRD: RN-12 | SPEC: REQ-012 | SL-04, SL-06, SL-09, SL-28, SL-29 |
| PRD: RN-13 | SPEC: REQ-013 | SL-D01, SL-12, SL-18 |
| PRD: RN-14 | SPEC: REQ-014 | SL-26, SL-28, SL-30 |
| PRD: RN-15 | SPEC: REQ-015 | SL-24, SL-31 |

### Cenários de negócio: localização do trabalho incremental

| PRD | Slices que explicitam o cenário |
| --- | --- |
| PRD: C01 | SL-01, SL-D02 e SL-D03 (parcial), SL-19, SL-21, SL-25 |
| PRD: C02 | SL-01, SL-03, SL-17, SL-24, SL-25 |
| PRD: C03 | SL-02, SL-D03, SL-21 |
| PRD: C04 | SL-D02 (parcial), SL-19, SL-20 |
| PRD: C05 | SL-26, SL-27, SL-30 |
| PRD: C06 | SL-26, SL-29, SL-30 |
| PRD: C07 | SL-01, SL-02 |
| PRD: C08 | SL-D01, SL-D03, SL-12, SL-21, SL-28 |
| PRD: C09 | SL-12 |
| PRD: C10 | SL-10, SL-D01, SL-D03, SL-12 |
| PRD: C11 | SL-11 |
| PRD: C12 | SL-10, SL-13 |
| PRD: C13 | SL-14 |
| PRD: C14 | SL-14 |
| PRD: C15 | SL-15 |
| PRD: C16 | SL-15 |
| PRD: C17 | SL-04, SL-14 |
| PRD: C18 | SL-04, SL-14 |
| PRD: C19 | SL-14 |
| PRD: C20 | SL-D01, SL-12, SL-18 |
| PRD: C21 | SL-05, SL-D01, SL-12, SL-15 |
| PRD: C22 | SL-05 |
| PRD: C23 | SL-05, SL-17 |
| PRD: C24 | SL-06, SL-07 |
| PRD: C25 | SL-06 |
| PRD: C26 | SL-07, SL-23 |
| PRD: C27 | SL-07, SL-08, SL-23 |
| PRD: C28 | SL-16 |
| PRD: C29 | SL-16 |
| PRD: C30 | SL-16, SL-23 |
| PRD: C31 | SL-22 |
| PRD: C32 | SL-23 |
| PRD: C33 | SL-23 |
| PRD: C34 | SL-23, SL-29 |
| PRD: C35 | SL-04, SL-09, SL-28 |
| PRD: C36 | SL-06, SL-09, SL-24, SL-28 |
| PRD: C37 | SL-16 |
| PRD: C38 | SL-09, SL-24, SL-29 |
| PRD: C39 | SL-26, SL-28, SL-30 |
| PRD: C40 | SL-18, SL-25, SL-30 |
| PRD: C41 | SL-08 |
| PRD: C42 | SL-17 |
| PRD: C43 | SL-14 |
| PRD: C44 | SL-D01, SL-D03, SL-12, SL-21, SL-24 |
| PRD: C45 | SL-07 |
| PRD: C46 | SL-12, SL-18 |

Cenários parciais são identificados no próprio bloco; D0 usa C01/C04 apenas parcialmente porque o bot foi criado fora do app. C01 integral fecha no percurso SL-21 e no gate SL-25. Os gates SL-25/SL-30 exigem a suíte aplicável completa, inclusive exemplos dos esquemas de cenário, mesmo quando um ID não é repetido na lista curta de fontes do gate.

### Falhas técnicas: localização da injeção

| SPEC | Slices que explicitam a falha |
| --- | --- |
| SPEC: FT-01 | SL-09 |
| SPEC: FT-02 | SL-04 |
| SPEC: FT-03 | SL-06 |
| SPEC: FT-04 | SL-07 |
| SPEC: FT-05 | SL-06 |
| SPEC: FT-06 | SL-13 |
| SPEC: FT-07 | SL-16 |
| SPEC: FT-08 | SL-09 |
| SPEC: FT-09 | SL-01 |
| SPEC: FT-10 | SL-11 |
| SPEC: FT-11 | SL-09, SL-14 |
| SPEC: FT-12 | SL-D01 (parcial), SL-12, SL-18 |
| SPEC: FT-13 | SL-23 |
| SPEC: FT-14 | SL-13, SL-32 |
| SPEC: FT-15 | SL-D01 (parcial), SL-12, SL-18 |

FT-14 é dividido entre revogação de conhecimento em SL-13 e exclusão completa em SL-32. FT-11 é exercitado na recuperação de execução em SL-09 e no contexto da IA em SL-14. Gates reaproveitam evidência compatível com a revisão atual e reexecutam quando há mudança, falha ou lacuna.

### Retomada final

O próximo trabalho previsto para D0 é **SL-10**, após conferir suas condições de liberação e obter o pedido específico de implementação. SL-D01–SL-D03 seguem suas dependências e decisões de credenciais/modelo/ambiente; o plano não os autoriza automaticamente. SL-00–SL-09 permanecem concluídos conforme o harness. Começar pelo resultado/Source IDs do bloco escolhido e terminar com critérios, evidências e handoff atualizados.
