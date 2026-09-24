# PRD v1 — LeadFlow.IA

**Produto:** agente SDR de IA para atendimento comercial multicanal.

**Versão:** 1.1 · **Data:** 24/09/2026 · **Status:** proposta para validação de negócio; decisão D0 documentada.

**Contexto:** MVP acadêmico de Métodos e Aplicações de IA, com perspectiva de evolução para SaaS.

**Entrega deste documento:** problema, valor, escopo, jornadas, regras e critérios de aceite. A especificação técnica será produzida após a aprovação deste PRD.

## 1. Resumo executivo

O LeadFlow.IA permite que uma empresa configure um agente SDR para receber contatos, esclarecer dúvidas com informações da própria empresa, coletar necessidades, qualificar oportunidades, registrar o histórico, acompanhar conversas e encaminhar o atendimento a uma pessoa.

A proposta é reduzir demora no primeiro atendimento e trabalho repetitivo dos vendedores, preservando o controle humano e a continuidade do processo comercial. O agente prepara a oportunidade; a conclusão da venda permanece sob responsabilidade humana neste MVP.

O primeiro marco é a jornada completa no Telegram. O ciclo inclui também WhatsApp não oficial como segunda prioridade obrigatória, demonstrando o mesmo comportamento comercial em dois canais. Voz é condicional; WhatsApp oficial é evolução futura. Uma demonstração apenas no Telegram comprova o primeiro marco, mas não conclui o escopo multicanal.

## 2. Fontes, precedência e limites de evidência

| ID | Fonte consultada | Contribuição |
| --- | --- | --- |
| F01 | [Ideação do Agente SDR](../docs/Ideação%20do%20Agente%20SDR%20%281%29.docx), texto e 19 imagens | Problema, atores, funcionalidades, funil, controle humano e jornada de sucesso |
| F02 | [Documento de definição de escopo](../docs/documento-definicao-escopo.md%20%281%29.pdf), seis páginas | Prioridade dos canais, limites do ciclo, riscos e critérios multicanal |
| F03 | [Plano de desenvolvimento](../docs/plano-desenvolvimento-codex.md) | Nome do produto, self-service, acompanhamento temporizado e marcos de evolução |

**Precedência:** o pedido atual define um PRD de negócios; F02 prevalece sobre F01 nos conflitos de escopo, conforme F03. F03 complementa a experiência pretendida, sem tornar sua arquitetura ou seus comandos decisões deste PRD.

**Legenda de maturidade:** **[D] documentado** significa presente nas fontes, não implementação comprovada; **[P] proposto** significa detalhamento de produto elaborado aqui, sujeito à aprovação; **[V] validar** significa decisão ainda aberta. Os critérios e cenários derivados de uma proposta só se tornam compromisso após sua aprovação.

No retrato da elaboração original, o repositório estava na branch `main`, sem aplicação ou testes encontrados. Esse retrato histórico não descreve o estado após SL-00–SL-09; consultar o harness para implementação e evidências atuais. `CONTEXT.md` e a constituição ainda eram modelos sem vocabulário preenchido; as definições abaixo foram propostas para alinhamento.

F02 cita pesquisas de concorrência, precificação e planilhas de custos que não estão na pasta `docs`. Portanto, não há evidência disponível para declarar demanda validada, exclusividade competitiva, margem ou preço aprovado. Estimativas financeiras, limites de plataformas e promessas de provisionamento das fontes precisam de validação própria; não são garantias deste PRD.

## 3. Problema e oportunidade

### 3.1 Problema sob a perspectiva do usuário

O gestor perde visibilidade de contatos que chegam pelos canais de conversa. Os vendedores repetem explicações, recebem oportunidades sem contexto e deixam retornos para depois. O lead espera, repete informações e pode desistir antes de falar com a pessoa adequada. Fora do horário da equipe, essa descontinuidade tende a ser mais perceptível. [D: F01 §§2–5]

### 3.2 Público e necessidade principal

| Ator | Necessidade | Resultado esperado |
| --- | --- | --- |
| Gestor da empresa | Organizar atendimento e controlar a automação | Operação configurável, oportunidades visíveis e intervenção simples |
| Vendedor/atendente | Receber contexto e saber o que fazer em seguida | Menos repetição e encaminhamento acionável |
| Lead | Obter informação confiável e avançar na compra | Resposta útil, continuidade e acesso a humano |
| Equipe avaliadora | Verificar a tese do projeto | Demonstração repetível em empresas e canais distintos |

O público inicial são pequenas e médias empresas com vendas iniciadas por conversa. O segmento da demonstração permanece aberto. O MVP usa um negócio demonstrativo principal e uma segunda organização sintética para verificar personalização e isolamento; isso não equivale a entregar templates completos de dois setores. [D/P]

**Necessidade central:** “Quando um interessado entrar em contato, quero atendê-lo com informações corretas, entender sua necessidade e entregar ao vendedor um próximo passo claro, sem perder o histórico.”

### 3.3 Hipóteses a validar

- H01: atendimento inicial automatizado reduz o tempo até uma resposta útil.
- H02: oportunidades com contexto e qualificação reduzem o esforço de triagem humana.
- H03: follow-ups oportunos recuperam conversas sem aumentar contatos indesejados.
- H04: um gestor consegue configurar e operar o produto pelo aplicativo web sem intervenção técnica.
- H05: configurações por empresa sustentam respostas pertinentes em mais de um canal.

O projeto acadêmico demonstra viabilidade funcional. Ganho de conversão, disposição a pagar e retenção exigem piloto posterior; não podem ser inferidos somente de conversas simuladas.

## 4. Objetivos e medição

**Objetivo principal:** transformar contatos recebidos em oportunidades registradas e acionáveis, com informações confiáveis e continuidade entre IA e equipe.

| ID | Indicador e definição | Critério desta versão |
| --- | --- | --- |
| OBJ-01 | Ativação: empresas que completam configuração e primeira conversa válida / empresas que iniciam onboarding | Jornada demonstrável sem intervenção técnica; meta percentual de piloto em V08 |
| OBJ-02 | Tempo até primeira resposta útil: recebimento do contato até resposta pertinente aceita pelo canal; mediana e p95 | Medir separadamente por canal; alvo depende da validação V08 |
| OBJ-03 | Qualificação correta: conversas com classificação compatível com a rubrica / conversas avaliadas | Todos os casos obrigatórios da suíte aprovada corretos; meta de piloto em V08 |
| OBJ-04 | Encaminhamento completo: transferências com motivo, histórico, resumo ou pendência explícita e responsável ou fila / transferências solicitadas | 100% nos cenários de aceite [P] |
| OBJ-05 | Continuidade: casos sem perda de contexto, duplicação de ação ou bloqueio silencioso / casos de falha e retomada | 100% nos cenários de aceite [P] |
| OBJ-06 | Retomada por follow-up: leads que respondem ao acompanhamento / leads com acompanhamento enviado | Medir separadamente de conversão; sem meta inventada |
| OBJ-07 | Proteções: vazamentos entre empresas, afirmações comerciais sem suporte e envios após bloqueio reconhecido | Zero ocorrências na suíte de aceite [P] |
| OBJ-08 | Custo operacional por conversa e por oportunidade aceita pelo vendedor | Levantar consumo e custo dos serviços; orçamento em V08 |

Usar janela e amostra declaradas, contar leads únicos dentro de cada organização/canal e separar testes de uso real. Uma confirmação de envio pelo canal não prova leitura pelo destinatário. Atribuir recuperação a follow-up requer janela definida no piloto; correlação não comprova incremento de vendas.

## 5. Escopo e marcos de entrega

| Marco | Entrega de negócio | Condição de conclusão |
| --- | --- | --- |
| D0 — Demonstração Telegram | Conta no aplicativo, poucos produtos cadastrados, bot criado previamente pelo responsável e vinculado no aplicativo, primeira resposta com API da OpenAI apoiada no catálogo e histórico visível | Jornada de ponta a ponta com contas e dados de teste controlados; critérios D0 abaixo. É entrega parcial e não conclui M1 |
| M1 — Jornada Telegram | Conta, empresa, um agente, conhecimento, produtos, vendedores, canal, CRM, qualificação, follow-up e controle humano | Jornada completa da seção 13 e cenários aplicáveis aprovados |
| M2 — Validação multicanal | Mesma operação comercial no WhatsApp não oficial, conexão e recuperação pelo aplicativo | Repetição dos resultados comerciais essenciais no segundo canal; obrigatório para concluir o ciclo |
| M3 — Voz condicional | Experiência de conversa por voz | Só entra mediante decisão de viabilidade, esforço e critérios próprios; não bloqueia M1/M2 |
| Evolução | WhatsApp oficial | Fora da entrega deste ciclo |

### Decisão D0 — apresentação em aproximadamente quatro dias (24/09/2026)

O solicitante autorizou preparar o bot Telegram antes da apresentação e vinculá-lo ao aplicativo; o atendimento da demonstração usará algum modelo da API da OpenAI. O modelo específico, credencial, orçamento e ambiente de webhook ainda precisam ser definidos antes da implementação dependente. O token do bot e a chave da OpenAI são segredos de configuração: não entram no código, repositório, histórico ou evidências. A autorização cobre o planejamento desta demonstração; chamadas pagas, conexão externa e publicação exigem as condições operacionais aplicáveis.

**Aceite D0:** o gestor cria conta/empresa no web app, cadastra produtos sintéticos, vincula no app seu bot preexistente, ativa explicitamente o agente e observa uma pergunta enviada por uma conta Telegram de teste receber resposta fundamentada no catálogo, com histórico no aplicativo. Informação comercial ausente, conflitante ou produto indisponível não vira afirmação inventada; há caminho visível para humano. Reentrega de webhook não duplica conversa ou resposta e envio incerto não é repetido cegamente. Uma segunda organização sintética não lê produtos/conversas/segredos da primeira.

**Limite D0:** a criação prévia do bot é intervenção externa assumida e não satisfaz a condição sem intervenção técnica de C01 nem encerra V01. D0 não comprova upload de documentos, qualificação, follow-up, WhatsApp, piloto, qualidade geral do modelo ou M1/M2. V02/V09 ficam delimitadas à configuração e ao catálogo sintéticos da demonstração; decisões completas continuam abertas para os marcos originais.

**Incluído [D]:** aplicativo web em português do Brasil; configuração self-service; um agente por empresa; um bot Telegram por empresa; CRM interno simples; produtos/serviços genéricos; conhecimento próprio; cadastro e atribuição de vendedores; histórico, resumo, classificação e estágio; atendimento humano; follow-ups por regras de tempo; separação entre empresas.

**Delimitação proposta [P]:** texto é a experiência obrigatória. Receber mídia não suportada deve produzir uma saída compreensível e preservar a conversa; compreensão de áudio, imagens e arquivos enviados pelo lead depende de V06. O envio de documentos pelo gestor para a base de conhecimento é uma capacidade distinta.

**Fora do escopo [D/P]:** prospecção fria e campanhas em massa; CRM externo; Instagram e anúncios; ERP; cobrança automatizada e planos; aplicativo nativo; múltiplos agentes simultâneos por empresa; múltiplos números de WhatsApp por empresa; múltiplos idiomas; analytics avançado; previsão de vendas; otimização autônoma do agente; templates completos por segmento; agenda externa, pagamentos, contratos e fechamento autônomo de vendas; infraestrutura de alta disponibilidade. Unificação automática da identidade de uma pessoa entre canais também não integra o MVP proposto.

## 6. Vocabulário e responsabilidades

| Termo | Definição de negócio |
| --- | --- |
| Organização/empresa | Cliente do produto; unidade de configuração, acesso e separação de dados |
| Agente SDR | Assistente comercial configurado para uma organização, operando dentro de regras aprovadas |
| Lead | Contato interessado; não confundir com a empresa cliente da plataforma |
| Conversa | Histórico de interações em um canal, com modo de atendimento definido |
| Qualificação | Avaliação de aderência, necessidade e intenção segundo critérios da empresa |
| Classificação/score | Síntese da qualificação; não é certeza de compra nem resultado financeiro |
| Encaminhamento/handoff | Passagem da responsabilidade de atendimento para a equipe, com contexto |
| Follow-up | Retomada contextual de conversa já iniciada pelo lead, conforme elegibilidade |
| Pendência operacional | Ação que não pôde ser concluída e está visível, com motivo e possibilidade de tratamento |

**Permissões propostas [P]:** gestor configura a organização, vê seu CRM e redistribui atendimentos. Vendedor autorizado vê e responde às conversas atribuídas e atualiza seu andamento, sem alterar configurações globais. Cadastro de vendedor não concede automaticamente acesso: o modo de habilitar esse acesso depende de V05. Nenhum desses papéis acessa outra organização por mera troca de endereço ou identificador.

## 7. Jornadas principais

### J01 — Configurar e ativar

Gestor cria conta e empresa → configura nome, identidade e instruções do agente → fornece conhecimento comercial → cadastra produtos/serviços e vendedores → define qualificação e acompanhamento → conecta o canal → verifica prontidão → ativa o atendimento.

Erros devem preservar o progresso e indicar a etapa que exige correção. Uma conexão solicitada não é uma conexão concluída. Enquanto o agente estiver inativo, não deve atender automaticamente. [D/P]

### J02 — Atender e qualificar

Lead inicia conversa → agente identifica a empresa e o contexto → responde com conhecimento válido → coleta apenas dados pertinentes → registra fatos e pendências → aplica critérios de qualificação → continua o atendimento ou encaminha.

Falta de telefone, orçamento ou prazo não autoriza inventar esses dados. Uma solicitação de humano interrompe a coleta obrigatória; o lead não deve ficar preso em um questionário. [P]

### J03 — Acompanhar sem insistência indevida

Conversa fica sem resposta → regra habilitada identifica elegibilidade → próximo acompanhamento fica visível → condições são reavaliadas antes do envio → mensagem contextual é enviada ou cancelada com motivo.

Uma resposta, pedido de interrupção, atendimento humano ou encerramento invalida os acompanhamentos antigos. Uma nova rodada de qualificação pode gerar novo agendamento conforme política, sem reativar automaticamente os antigos. [D/P]

### J04 — Transferir e concluir

Gatilho de transferência → pausa da automação na conversa → registro do motivo e contexto → atribuição a vendedor elegível ou fila pendente → humano assume → negocia e atualiza o resultado.

O produto deve diferenciar “encaminhamento solicitado” de “humano assumiu”. Sem vendedor disponível, a oportunidade continua visível para o gestor. Não se promete resposta imediata ou prazo que a empresa não definiu. [P]

### J05 — Recuperar uma interrupção

Falha identificada → estado e impacto visíveis → contexto preservado → recuperação automática limitada ou ação humana indicada → retomada somente de ações ainda válidas.

Uma falha em um canal ou uma conversa não deve bloquear a outra operação disponível. A recuperação não pode despejar follow-ups vencidos nem repetir uma resposta cuja entrega já foi confirmada. [P]

## 8. Histórias de usuário

1. **US-01:** Como gestor, quero criar conta e empresa para iniciar uma operação própria.
2. **US-02:** Como gestor, quero acessar minha operação autenticado para proteger suas informações.
3. **US-03:** Como gestor, quero retomar uma configuração incompleta para não repetir trabalho.
4. **US-04:** Como gestor, quero definir nome, identidade e instruções do agente para representar meu negócio.
5. **US-05:** Como gestor, quero fornecer e atualizar conhecimento para manter respostas comerciais corretas.
6. **US-06:** Como gestor, quero conhecer o estado de disponibilização de um documento para saber se o agente já pode usá-lo.
7. **US-07:** Como gestor, quero cadastrar produtos, preços e disponibilidade para orientar ofertas pertinentes.
8. **US-08:** Como gestor, quero definir critérios de qualificação para reconhecer oportunidades úteis à minha equipe.
9. **US-09:** Como gestor, quero cadastrar vendedores e sua disponibilidade para encaminhar corretamente.
10. **US-10:** Como gestor, quero conectar o Telegram pelo aplicativo para iniciar atendimento sem configuração técnica externa.
11. **US-11:** Como gestor, quero conectar o WhatsApp e acompanhar seu estado para operar o segundo canal.
12. **US-12:** Como gestor, quero entender os impedimentos de ativação para corrigi-los antes de atender.
13. **US-13:** Como gestor, quero ativar e desativar o agente para controlar a automação.
14. **US-14:** Como lead, quero receber uma resposta contextual em português para esclarecer minha necessidade.
15. **US-15:** Como lead, quero receber informações comerciais fundamentadas para tomar decisões com confiança.
16. **US-16:** Como lead, quero corrigir dados informados para não ser qualificado a partir de informações erradas.
17. **US-17:** Como lead, quero recusar uma informação sem bloquear o contato humano.
18. **US-18:** Como lead, quero voltar à conversa com meu contexto preservado para evitar repetição.
19. **US-19:** Como lead, quero solicitar uma pessoa a qualquer momento para tratar o que a automação não resolve.
20. **US-20:** Como lead, quero entender o que fazer quando minha mensagem não pode ser interpretada.
21. **US-21:** Como lead, quero receber apenas acompanhamentos pertinentes a uma conversa que iniciei.
22. **US-22:** Como lead, quero interromper mensagens automáticas para respeitar minha preferência.
23. **US-23:** Como vendedor, quero receber histórico, necessidade e motivo do encaminhamento para continuar o atendimento.
24. **US-24:** Como vendedor, quero assumir a conversa sem respostas concorrentes da IA.
25. **US-25:** Como vendedor, quero responder pelo aplicativo para manter a continuidade no canal de origem.
26. **US-26:** Como vendedor, quero corrigir a classificação e atualizar o estágio para refletir a realidade comercial.
27. **US-27:** Como vendedor, quero registrar ganho ou perda com contexto para concluir o acompanhamento.
28. **US-28:** Como gestor, quero visualizar leads por estágio, classificação e responsável para priorizar trabalho.
29. **US-29:** Como gestor, quero identificar oportunidades sem responsável para impedir abandono silencioso.
30. **US-30:** Como gestor, quero redistribuir atendimentos para cobrir indisponibilidade da equipe.
31. **US-31:** Como gestor, quero definir limites e horários de follow-up para controlar a experiência de contato.
32. **US-32:** Como gestor, quero identificar falhas e ações pendentes para recuperar a operação.
33. **US-33:** Como gestor, quero que alterações manuais sejam preservadas para manter controle sobre a automação.
34. **US-34:** Como gestor, quero dados separados por organização para proteger meus clientes e meu negócio.
35. **US-35:** Como gestor, quero compreender a razão da qualificação para revisar decisões do agente.
36. **US-36:** Como avaliador, quero repetir a jornada em dois canais para comprovar a consistência do produto.
37. **US-37:** Como avaliador, quero comparar duas empresas com dados distintos para comprovar a personalização.
38. **US-38:** Como gestor, quero medir qualidade, esforço e custo para decidir sobre continuidade do piloto.

## 9. Requisitos e critérios de aceite de negócio

Os itens abaixo descrevem comportamento observável. **[D/P]** indica capacidade documentada com regras de borda propostas; não representa aprovação prévia desses detalhes.

### RN-01 — Conta, acesso e isolamento [D/P: F01 §§6, 14, 24]

- Conta autenticada opera somente organizações e conversas autorizadas. Resumos, buscas, documentos, produtos e indicadores respeitam a mesma separação.
- Acesso negado não revela informações comerciais de outra empresa. Perda de sessão exige autenticação antes de nova alteração.
- Contatos com identificadores iguais em empresas diferentes permanecem separados.

### RN-02 — Configuração e prontidão [D/P: F01 §§6, 19; F03 §1]

- Um agente por empresa; nome, instruções, conhecimento, catálogo, vendedores e regras são gerenciados pelo aplicativo.
- Proposta de prontidão: instruções salvas, ao menos uma fonte comercial utilizável, canal operacional, critérios de qualificação e um responsável de contingência definido. Dados adicionais obrigatórios dependem de V02.
- A ativação incompleta informa exatamente o que falta. Salvar configuração não ativa o agente implicitamente.
- Alterações confirmadas valem para novas decisões; o histórico mantém o que foi dito anteriormente. Respostas ainda não enviadas devem respeitar desativação e mudanças comerciais já confirmadas.

### RN-03 — Conexão dos canais [D/P: F02 §§4, 8; F03 §§1, 4]

- Telegram: experiência desejada de criação/configuração pelo aplicativo, com identidade própria da empresa e indicação de sucesso ou falha. O mecanismo e sua viabilidade dependem de V01.
- WhatsApp não oficial: conexão por QR code, com distinção entre aguardando conexão, conectado e desconectado. QR expirado permite nova tentativa sem recriar a empresa.
- Tentativas repetidas não criam múltiplos canais ativos para o mesmo pedido. Falha em um canal não altera o estado do outro.
- Conexão manual provisória pode apoiar testes, mas não comprova aceite do onboarding self-service final.

### RN-04 — Conhecimento e catálogo confiáveis [D/P: F01 §§22–23; F03 §3]

- O gestor distingue conteúdo em preparação, utilizável e com falha. Conteúdo com falha não é apresentado como disponível.
- Preço, produto, disponibilidade e política precisam de suporte em conteúdo válido da empresa. O agente não completa lacunas com suposição.
- Fonte ausente, conflitante ou insuficiente provoca esclarecimento ou encaminhamento, sem afirmação comercial categórica.
- Produto indisponível não é apresentado como comprável. Alternativa só é oferecida se estiver cadastrada e pertinente.
- Remoção ou atualização confirmada deve impedir que novas respostas usem informação comercial invalidada. Formatos e limites de documentos serão definidos em V06.

### RN-05 — Conversa e coleta progressiva [D/P: F01 §§7, 10, 21]

- Conversa usa português do Brasil, mantém contexto e coleta interesse, necessidade e demais campos definidos pela empresa, sem exigir tudo na primeira interação.
- Dado desconhecido fica desconhecido; recusa e correção ficam registradas sem fabricação de telefone, orçamento ou prazo.
- O mesmo contato no mesmo canal/empresa retoma seu registro. Sem evidência suficiente, nomes iguais e contatos em canais diferentes não são fundidos automaticamente.
- Conteúdo não suportado gera orientação ou acesso a humano; não é interpretado como silêncio nem como intenção de compra.
- Instruções enviadas pelo lead ou contidas em documentos não autorizam burlar regras, revelar instruções internas ou acessar outra empresa.

### RN-06 — Qualificação explicável [D/P: F01 §§3, 6, 9, 21]

- Proposta: classificações `não avaliado`, `frio`, `morno` e `quente`, sempre acompanhadas de evidências e lacunas.
- A rubrica da empresa define aderência à oferta, necessidade e intenção; orçamento e prazo só são obrigatórios se a empresa assim aprovar. Não se presume uma metodologia comercial universal.
- Lead quente deve cumprir os critérios acordados e ter intenção compatível. Informação insuficiente não equivale a desqualificação nem justifica classificação quente.
- Pedido explícito de humano independe de score. Correção humana de classificação exige motivo e prevalece até revisão autorizada.
- Score numérico, pesos e limiares não estão definidos nas fontes; permanecem em V03. A IA não pode escolher silenciosamente sua própria política.

### RN-07 — CRM e rastreabilidade [D/P: F01 §21 e imagem do funil]

- Registrar identificação disponível, canal/origem, interesse, dados coletados, classificação, estágio, responsável, histórico, resumo, último contato e próximo follow-up.
- Resumo distingue fatos, dúvidas e próximo passo; ausência ou falha de resumo não impede acesso ao histórico nem transferência.
- Alterações relevantes indicam autor — IA ou pessoa —, momento e motivo. Campos desconhecidos não aparecem como confirmados.
- Filtros essenciais: estágio, classificação e responsável, incluindo ausência de responsável.
- A confirmação de uma atualização exige que ela esteja registrada. Em falha, mostrar pendência e preservar os dados anteriores.

### RN-08 — Gatilhos e execução do encaminhamento [D/P: F01 §§9–10]

- Encaminhar por lead quente, solicitação explícita, falta de conhecimento, assunto sensível ou regra da empresa.
- Registrar motivo, contexto, fatos coletados, dúvidas e próximo passo. Não exigir qualificação completa para atender pedido humano.
- Separar atribuição de responsabilidade da efetiva assunção da conversa. Vendedor elegível deve estar ativo e disponível segundo política validada.
- Sem elegível, manter fila pendente visível ao gestor; a IA não simula atendimento humano nem promete prazo inexistente.
- Indisponibilidade, ausência de resumo ou falha ao atribuir não pode descartar o lead ou reiniciar o fluxo indefinidamente.

### RN-09 — Controle humano e prioridade [D/P: F01 §10]

- Assumir conversa suspende respostas e follow-ups automáticos naquela conversa. Desativar agente suspende novas saídas automáticas em toda a empresa.
- Intervenção já confirmada deve prevalecer sobre resposta automática ainda não enviada. Envio já aceito pelo canal não pode ser tratado como recuperável por essa pausa; fica registrado.
- Duas pessoas não podem assumir simultaneamente a responsabilidade sem indicação de quem está atendendo. Reatribuição explícita registra a troca.
- Retorno à IA exige ação explícita de pessoa autorizada e reavaliação da elegibilidade. Reativação global não remove pausas humanas nem opt-out.

### RN-10 — Follow-up elegível e limitado [D/P: F01 §6 e fluxo ilustrado; F02 §6; F03 fase 4]

- Somente conversas iniciadas pelo lead podem receber acompanhamento. A IA redige; regras da empresa definem tempo, quantidade e condições.
- A política deve definir intervalo, máximo de tentativas, validade, janela e fuso. Os exemplos de 2h e 24h de F03 não constituem valores aprovados.
- Reavaliar imediatamente antes do envio: agente ativo, canal disponível, atendimento automático, ausência de resposta posterior, ausência de opt-out, oportunidade aberta e limite não atingido.
- Resposta posterior, assunção humana, opt-out, encerramento ou pausa global cancela agendamentos antigos. Novos acompanhamentos exigem nova elegibilidade.
- Ao atingir limite, registrar “sem resposta” como situação de acompanhamento, sem declarar automaticamente a oportunidade perdida.
- Após indisponibilidade, não acumular envios vencidos; reavaliar relevância e descartar os expirados. Política temporal final em V04.

### RN-11 — Interrupção de contatos [P]

- Pedido inequívoco de parar cancela follow-ups e bloqueia novas saídas automáticas para aquele contato no canal. Pode haver uma confirmação única, se aprovada em V04.
- Opt-out não é falha nem perda comercial automática. Fica visível para a equipe.
- Nova mensagem do lead pode ser registrada e encaminhada à equipe, mas não remove automaticamente o bloqueio. Forma de reautorização fica em V04.

### RN-12 — Falhas, duplicação e retomada [D/P: F01 §24; F03 fases 4 e 8]

- Reentrega da mesma mensagem não cria novo lead, nova resposta ou novo acompanhamento. Mensagens distintas com texto igual não são descartadas por essa semelhança.
- Atrasos não devem fazer uma mensagem antiga sobrescrever correção mais recente nem reabrir estado encerrado sem decisão válida.
- Distinguir envio confirmado, falha confirmada e resultado desconhecido. Não reenviar cegamente quando não se sabe se a primeira tentativa foi aceita.
- Toda ação impedida deve ter estado visível, motivo, responsável de tratamento e próxima ação. Esgotadas as tentativas permitidas, vai para tratamento humano.
- Não existe promessa de preservar mensagens que o canal nunca disponibilizou; eventuais lacunas de recebimento devem ser identificadas quando conhecidas, sem histórico fabricado.

### RN-13 — Limites de autonomia comercial [D/P: F01 §§9–10]

- O agente pode responder, consultar, coletar, classificar, atualizar CRM e encaminhar dentro das regras.
- Não concede desconto não autorizado, confirma pagamento, celebra contrato, garante resultado, realiza aconselhamento especializado ou marca venda ganha por inferência.
- Reclamação complexa, pedido de exceção ou assunto sensível deve chegar a humano com contexto. A natureza sensível depende da política da empresa, sem delegar ao agente decisões profissionais.

### RN-14 — Consistência entre empresas e canais [D/P: F02 §§2–4, 7]

- Mesmos fatos e regras devem produzir decisões comerciais equivalentes em Telegram e WhatsApp; não se exige redação idêntica.
- Mudar de canal não exige recadastrar conhecimento, catálogo e critérios da empresa. Particularidades de conexão e mídia ficam explícitas.
- Uma organização não influencia as respostas, produtos ou vendedores de outra. A personalização deve ser demonstrável com dados distintos.

### RN-15 — Proteção de dados e transparência [D/P: F01 §24]

- Coletar apenas o necessário à finalidade comercial e restringir leitura/alteração aos papéis autorizados.
- Proposta: identificar o atendimento automatizado e oferecer caminho compreensível para humano.
- Credenciais de canais não aparecem em conversas, resumos ou telas sem necessidade de uso.
- Antes de piloto com dados reais, definir aviso de privacidade, retenção, tratamento de pedidos de exclusão e responsáveis. O PRD não declara conformidade legal concluída; essa política depende de V07.

## 10. Estados e transições do processo

**Proposta de detalhamento [P], baseada no funil de F01.** Separar estágio comercial, modo de atendimento e situação operacional evita confundir “qualificado” com “atendido” ou “canal desconectado” com “lead perdido”.

| Estágio comercial | Entrada | Saída permitida |
| --- | --- | --- |
| Novo | Primeiro contato registrado | Em atendimento quando a interação começa |
| Em atendimento | Necessidade em investigação | Qualificado quando atende à rubrica; encaminhado se exige humano; perdido por decisão humana |
| Qualificado | Critérios atendidos com evidências | Encaminhado; retorno à avaliação por correção justificada |
| Encaminhado | Solicitação de atendimento humano registrada | Em negociação quando humano inicia tratativa; retorno à avaliação por decisão explícita |
| Em negociação | Pessoa responsável conduz a oportunidade | Ganho ou perdido por confirmação humana; outra revisão exige motivo |
| Ganho / Perdido | Resultado confirmado por pessoa autorizada | Reabertura apenas humana, com motivo e histórico preservado |

Encaminhamento pode ocorrer antes da qualificação. Não obriga o lead a passar por todos os estágios. Ausência de resposta não significa perda. Nova mensagem em oportunidade encerrada aparece para revisão humana, sem reativação automática de acompanhamento.

**Modo de atendimento:** `automático` → `aguardando humano` → `humano`; retorno a `automático` somente explícito. Pausa global da empresa e bloqueio de contato são restrições adicionais, não estágios comerciais.

**Acompanhamento:** `não elegível`, `agendado`, `cancelado`, `enviado`, `sem resposta`, `falha` ou `resultado desconhecido`. Apenas `enviado` comprova aceitação pelo canal, não leitura.

**Prioridade antes de qualquer saída automática:** bloqueio de contato → agente desativado → atendimento humano/aguardando humano → oportunidade encerrada → canal/ação indisponível → resposta ou follow-up elegível. Havendo impedimento, conservar contexto e indicar tratamento; não reiniciar a jornada.

## 11. Qualidade, operação e riscos

### 11.1 Condições mínimas de uso

- Gestor deve conseguir identificar a situação do agente, canal, documentos e conversas sem consultar ferramentas técnicas.
- Erros devem informar o que falhou e qual ação permite continuar; carregamento indefinido não é estado de negócio válido.
- Falhas devem ficar limitadas à operação afetada sempre que possível. Mensagens manuais também precisam de estado de envio verificável.
- Volume simultâneo, tempo de resposta, tempo máximo de espera e orçamento devem ser acordados antes do piloto; não há SLA aprovado nas fontes.
- Atendimento automatizado fora do expediente não implica vendedor humano disponível continuamente.

### 11.2 Riscos e tratamento de negócio

| Risco | Consequência | Tratamento e responsável proposto |
| --- | --- | --- |
| Informação comercial inventada ou desatualizada | Perda de confiança e promessa indevida | Gestor valida fontes; encaminhamento na ausência de suporte; RN-04/13 |
| Lead preso aguardando humano | Oportunidade abandonada | Fila visível, responsável de contingência e prazo operacional em V05 |
| Follow-up após resposta ou recusa | Incômodo e perda de confiança | Revalidação, cancelamento e limite; RN-10/11 |
| Desconexão/restrição do WhatsApp não oficial | Interrupção do segundo canal | Informar risco ao gestor, testar com números controlados, limitar contato ao escopo aprovado; não prometer ausência de bloqueio |
| Provisionamento Telegram inviável como descrito | Onboarding não entrega self-service | Validar V01 antes de compromisso de prazo; alternativa exige decisão explícita |
| Vazamento entre empresas | Exposição de dados | Critério impeditivo de aceite e teste cruzado; RN-01 |
| Falha com resultado de envio desconhecido | Resposta duplicada ou ausente | Reconciliação/tratamento explícito; RN-12 |
| Qualificação desalinhada ao negócio | Vendedor recebe oportunidades inadequadas | Rubrica validada e revisão humana; RN-06 |
| Custo operacional sem medição | Piloto economicamente inviável | Levantar consumo por empresa/conversa e definir orçamento; OBJ-08 |
| Expansão prematura de escopo | Núcleo comercial incompleto | Priorizar M1/M2; voz e expansões não consomem aceite obrigatório |

## 12. Estratégia de validação e cenários Gherkin

### 12.1 Fronteiras propostas para validação

Validar no nível mais próximo do resultado de negócio: ações do gestor no aplicativo, mensagens recebidas pelo lead, registros no CRM, fila humana e cancelamentos observáveis. O foco é a jornada completa, complementada por conversas de referência com rubricas conhecidas e simulação controlada de tempo e falhas.

F03 propõe conversas de referência e testes de jornada, mas nenhuma suíte executável foi encontrada. Os cenários abaixo são especificações de aceite, **não testes executados**. Ferramentas, componentes, contratos e automação serão definidos na SPEC. O solicitante confirmou a cobertura de toda a jornada e suas falhas durante a elaboração; essa confirmação não equivale à aprovação integral do PRD.

**Massa proposta:** empresas fictícias Alfa e Beta, catálogos diferentes, gestor e vendedor por empresa, lead com e sem telefone, vendedor ativo/inativo e regras temporais explícitas por teste. Não usar dados reais. Valores nos exemplos servem apenas à massa, sem fixar política comercial global.

**Prioridade:** C01–C46 compõem o aceite obrigatório das regras aprovadas; C05, C06 e C39 são específicos de M2. Casos envolvendo propostas aguardam sua aprovação. Reexecutar os cenários de conversa, encaminhamento e acompanhamento nos dois canais quando aplicáveis. Não exigir frases exatas da IA: verificar fatos, decisões, registros e ausência de ações proibidas.

### 12.2 Acesso, configuração e canais

```gherkin
# language: pt
Funcionalidade: Preparar uma operação comercial controlada

  @C01 @RN01 @RN02
  Cenário: Criar uma operação e concluir a configuração
    Dado que um gestor ainda não possui uma organização
    Quando cria sua conta e empresa e completa os requisitos de prontidão
    E conecta o Telegram e ativa o agente pelo aplicativo
    Então a operação fica apta a receber uma conversa
    E nenhuma intervenção técnica externa é necessária

  @C02 @RN01
  Esquema do Cenário: Impedir acesso a dados de outra organização
    Dado que estou autenticado apenas na empresa Alfa
    Quando tento <acao> da empresa Beta por um identificador conhecido
    Então o acesso é negado sem revelar o conteúdo da Beta
    E nenhuma informação da Beta é alterada
    Exemplos:
      | acao                    |
      | ler uma conversa        |
      | consultar um documento  |
      | atribuir um lead        |
      | consultar um resumo     |
      | consultar indicadores   |

  @C03 @RN02
  Cenário: Impedir ativação incompleta e preservar progresso
    Dado que o gestor salvou as instruções mas não tem fonte comercial utilizável
    Quando tenta ativar o agente
    Então a ativação é recusada com a pendência identificada
    E as instruções permanecem salvas para continuidade

  @C04 @RN03
  Cenário: Recuperar falha no provisionamento Telegram
    Dado que a criação do canal foi solicitada e o resultado ainda não é conclusivo
    Quando o gestor repete a solicitação
    Então o produto apresenta o estado do pedido existente
    E não cria um segundo canal ativo para o mesmo pedido
    E se houver falha confirmada apresenta uma forma de retomar

  @C05 @RN03
  Cenário: Recuperar QR code expirado
    Dado que a empresa iniciou a conexão do WhatsApp
    Quando o QR code expira antes da leitura
    Então o canal não é apresentado como conectado
    E o gestor pode solicitar novo QR code sem refazer a empresa

  @C06 @RN03 @RN12
  Cenário: Isolar a desconexão de um canal
    Dado que Telegram e WhatsApp estão conectados
    Quando o WhatsApp desconecta
    Então o gestor vê a indisponibilidade e a ação de reconexão
    E o Telegram continua elegível para atendimento
    E envios do WhatsApp não aparecem como confirmados sem confirmação

  @C07 @RN01
  Cenário: Exigir autenticação para alteração após expiração de sessão
    Dado que a sessão de um gestor expirou
    Quando tenta modificar as instruções do agente
    Então a alteração não é aplicada
    E o aplicativo solicita autenticação
```

### 12.3 Atendimento, conhecimento e qualificação

```gherkin
# language: pt
Funcionalidade: Atender com informação confiável e registrar a oportunidade

  @C08 @RN04 @RN05 @RN07
  Cenário: Responder e registrar uma oportunidade
    Dado que a empresa Alfa possui um serviço disponível com preço de teste de 100 reais
    Quando um novo lead pergunta sobre esse serviço
    Então recebe uma resposta compatível com a informação válida da Alfa
    E o CRM registra o contato, a origem e o histórico

  @C09 @RN04 @RN08
  Esquema do Cenário: Não fabricar informação comercial
    Dado que a informação solicitada está <condicao>
    Quando o lead faz a pergunta comercial
    Então o agente não apresenta uma afirmação categórica sem suporte
    E encaminha a dúvida para tratamento humano com contexto
    Exemplos:
      | condicao                         |
      | ausente da base                  |
      | conflitante entre fontes válidas |
      | indisponível por falha de consulta|

  @C10 @RN04
  Cenário: Não oferecer produto indisponível como comprável
    Dado que um produto está marcado como indisponível
    Quando o lead pergunta se pode comprá-lo
    Então o agente informa a indisponibilidade conhecida
    E não inventa prazo de reposição ou alternativa não cadastrada

  @C11 @RN04
  Cenário: Tornar falha de documento recuperável
    Dado que o gestor enviou um documento para disponibilização
    Quando o processamento falha
    Então o documento aparece com falha e opção de correção
    E seu conteúdo não é tratado como conhecimento utilizável
    E outras fontes válidas continuam disponíveis

  @C12 @RN04 @RN02
  Cenário: Respeitar informação comercial atualizada
    Dado que o gestor confirmou a substituição de um preço antigo
    Quando uma resposta sobre preço ainda não enviada é concluída
    Então ela respeita a informação comercial vigente
    E o histórico anterior não é reescrito

  @C13 @RN05 @RN06
  Cenário: Coletar sem inventar dados ausentes
    Dado que o canal não informou o telefone do lead
    E o lead não quer informar orçamento
    Quando a conversa prossegue
    Então telefone e orçamento não são preenchidos por suposição
    E o lead continua podendo solicitar atendimento humano

  @C14 @RN05 @RN06 @RN07
  Cenário: Corrigir uma informação usada na qualificação
    Dado que o lead informou uma necessidade anteriormente
    Quando corrige essa necessidade
    Então a informação atual e a avaliação passam a refletir a correção
    E o histórico preserva a mudança sem apresentar o dado antigo como atual

  @C15 @RN06 @RN08
  Cenário: Identificar lead quente com base na rubrica
    Dado que a empresa aprovou seus critérios de lead quente
    E a conversa contém evidências suficientes para todos esses critérios
    Quando o agente avalia a oportunidade
    Então registra a classificação e suas evidências
    E solicita encaminhamento humano

  @C16 @RN06
  Cenário: Evitar qualificação positiva com dados insuficientes
    Dado que faltam evidências exigidas pela rubrica da empresa
    Quando o agente avalia o lead
    Então não o classifica como quente apenas por linguagem entusiasmada
    E registra as lacunas que precisam de esclarecimento

  @C17 @RN05 @RN12
  Cenário: Retomar o mesmo contato sem criar outro lead
    Dado que um contato tem histórico na empresa Alfa pelo Telegram
    Quando volta a enviar mensagem pelo mesmo contato e canal
    Então seu histórico anterior permanece acessível
    E a retomada não cria um lead duplicado

  @C18 @RN05
  Cenário: Não fundir pessoas apenas pelo nome
    Dado que existem dois contatos distintos com o mesmo nome
    Quando ambos conversam com a empresa
    Então seus dados não são misturados
    E a eventual presença em outro canal não provoca fusão automática

  @C19 @RN05 @RN08
  Cenário: Receber mídia não suportada sem bloquear a conversa
    Dado que o lead envia uma mídia cuja compreensão não é suportada
    Quando o agente recebe a mensagem
    Então informa a limitação e oferece texto ou atendimento humano
    E não inventa o conteúdo da mídia

  @C20 @RN01 @RN05 @RN13
  Cenário: Recusar instrução para violar limites do agente
    Dado que uma mensagem ou documento pede para ignorar as regras e revelar dados de outra empresa
    Quando esse conteúdo é considerado na conversa
    Então o agente não revela os dados nem executa a instrução proibida
    E mantém o atendimento dentro das regras autorizadas
```

### 12.4 Encaminhamento, controle humano e resultado

```gherkin
# language: pt
Funcionalidade: Transferir sem perder contexto ou responsabilidade

  @C21 @RN08 @RN09
  Esquema do Cenário: Encaminhar por gatilho obrigatório
    Dado que há uma conversa em atendimento automático
    Quando ocorre <gatilho>
    Então é registrado um encaminhamento com motivo e contexto
    E a automação comercial fica suspensa nessa conversa
    Exemplos:
      | gatilho                           |
      | solicitação explícita de humano   |
      | classificação quente fundamentada |
      | falta de conhecimento necessário  |
      | reclamação complexa               |
      | regra empresarial de transferência|

  @C22 @RN08
  Cenário: Encaminhar sem vendedor disponível
    Dado que nenhum vendedor está elegível
    Quando o lead solicita uma pessoa
    Então o encaminhamento aparece pendente para o gestor
    E o lead não recebe promessa de atendimento imediato
    E o histórico permanece disponível para futura assunção

  @C23 @RN07 @RN08
  Cenário: Falha no resumo não bloquear o humano
    Dado que um encaminhamento deve ocorrer
    Quando não é possível produzir o resumo
    Então o histórico e o motivo ficam disponíveis ao humano
    E a pendência de resumo fica indicada sem impedir a assunção

  @C24 @RN09
  Cenário: Assunção humana prevalecer sobre resposta automática pendente
    Dado que uma resposta automática ainda não foi enviada
    Quando um vendedor assume a conversa e recebe confirmação
    Então essa resposta automática não é enviada
    E a próxima resposta manual fica registrada com seu autor

  @C25 @RN09
  Cenário: Evitar assunção concorrente ambígua
    Dado que dois vendedores tentam assumir a mesma conversa
    Quando uma assunção é confirmada
    Então ambos visualizam o mesmo responsável atual
    E qualquer troca posterior exige reatribuição explícita

  @C26 @RN09 @RN10
  Cenário: Desativação global impedir automação pendente
    Dado que existem respostas e follow-ups ainda não enviados
    Quando o gestor desativa o agente e recebe confirmação
    Então novas saídas automáticas da empresa são impedidas
    E os acompanhamentos antigos são cancelados com motivo
    E o histórico permanece acessível

  @C27 @RN09 @RN11
  Cenário: Reativação global preservar restrições individuais
    Dado que uma conversa está sob controle humano e outra tem opt-out
    Quando o gestor reativa o agente da empresa
    Então nenhuma dessas conversas retorna automaticamente ao atendimento da IA

  @C28 @RN06 @RN07 @RN09
  Cenário: Preservar uma classificação corrigida por pessoa
    Dado que um vendedor corrigiu uma classificação e informou o motivo
    Quando uma avaliação automática anterior chega atrasada
    Então ela não sobrescreve a correção humana
    E a alteração válida permanece identificada no histórico

  @C29 @RN07 @RN13
  Cenário: Registrar conclusão somente com confirmação humana
    Dado que o lead declara intenção de comprar
    Quando o agente avalia essa intenção
    Então não marca a oportunidade como ganha por inferência
    Quando uma pessoa autorizada confirma o resultado comercial
    Então o resultado é registrado com autor e momento

  @C30 @RN07 @RN09 @RN10
  Cenário: Receber contato após encerramento
    Dado que uma oportunidade foi encerrada como ganha ou perdida
    Quando o contato envia nova mensagem
    Então a mensagem fica disponível para revisão humana
    E a oportunidade não é reaberta nem recebe follow-up automaticamente
```

### 12.5 Acompanhamento, tempo e falhas

```gherkin
# language: pt
Funcionalidade: Acompanhar e recuperar sem duplicar ou insistir indevidamente

  @C31 @RN10
  Cenário: Realizar um follow-up elegível
    Dado que o lead iniciou uma conversa e deixou de responder
    E a política de teste permite um acompanhamento no momento atual
    E não existe bloqueio ou transferência humana
    Quando chega o horário previsto e a elegibilidade é reavaliada
    Então um único acompanhamento contextual é enviado
    E seu estado e horário aparecem no CRM

  @C32 @RN10 @RN11
  Esquema do Cenário: Cancelar acompanhamento que perdeu elegibilidade
    Dado que um follow-up está agendado e ainda não foi enviado
    Quando ocorre <evento> antes do envio
    Então esse follow-up não é enviado
    E seu cancelamento fica registrado com o motivo
    Exemplos:
      | evento                    |
      | resposta do lead          |
      | assunção por humano        |
      | pedido para parar contatos |
      | encerramento da oportunidade|
      | desativação do agente     |

  @C33 @RN10
  Cenário: Respeitar janela, fuso e máximo de tentativas
    Dado que a política de teste define fuso, janela e número máximo de acompanhamentos
    Quando um agendamento cai fora da janela permitida
    Então nenhum envio ocorre fora da janela
    E a próxima ação respeita a validade definida na política
    Quando o limite de tentativas já foi atingido
    Então não é criado novo envio e a situação fica como sem resposta
    E a oportunidade não é marcada como perdida automaticamente

  @C34 @RN10 @RN12
  Cenário: Recuperar canal sem acumular follow-ups vencidos
    Dado que vários acompanhamentos venceram durante uma indisponibilidade
    Quando o canal volta a funcionar
    Então a elegibilidade e a validade de cada acompanhamento são reavaliadas
    E os expirados são descartados com motivo
    E não é enviada uma sequência acumulada de mensagens vencidas

  @C35 @RN05 @RN12
  Cenário: Reprocessar a mesma mensagem sem duplicar efeitos
    Dado que uma mensagem recebida já gerou registro e resposta confirmada
    Quando o canal entrega novamente a mesma mensagem
    Então não é criado outro lead, resposta ou follow-up para esse evento
    E uma mensagem distinta com texto igual continua podendo ser atendida

  @C36 @RN12
  Cenário: Tratar resultado desconhecido de envio
    Dado que foi tentado um envio sem confirmação conclusiva do canal
    Quando a operação excede o tempo de espera
    Então o envio fica com resultado desconhecido
    E não é marcado como entregue nem reenviado cegamente
    E existe uma ação de verificação ou tratamento humano

  @C37 @RN07 @RN12
  Cenário: Não confirmar atualização de CRM que falhou
    Dado que uma alteração de estágio foi solicitada
    Quando seu registro falha
    Então a alteração não aparece como concluída
    E os dados anteriores e o histórico continuam disponíveis
    E uma pendência permite nova tentativa ou tratamento humano

  @C38 @RN12
  Cenário: Encerrar tentativas de recuperação sem loop
    Dado que uma ação falhou até o limite de tentativas aprovado
    Quando ocorre a última falha
    Então não é iniciada uma repetição ilimitada
    E a operação fica pendente com motivo e responsável de tratamento
    E outras conversas elegíveis continuam operando

  @C39 @RN14
  Cenário: Preservar decisões comerciais nos dois canais
    Dado que a mesma empresa usa Telegram e WhatsApp com a mesma configuração
    Quando conversas de referência apresentam os mesmos fatos em ambos
    Então a qualificação e o gatilho de encaminhamento são equivalentes
    E o catálogo e o conhecimento não precisam ser recadastrados

  @C40 @RN01 @RN14
  Cenário: Personalizar sem misturar empresas
    Dado que Alfa e Beta possuem serviços, preços e vendedores diferentes
    Quando contatos fazem a mesma pergunta às duas empresas
    Então cada resposta usa apenas o contexto da empresa destinatária
    E cada lead é atribuído somente dentro de sua própria empresa

  @C41 @RN11
  Cenário: Não remover opt-out por uma nova mensagem
    Dado que um contato pediu para interromper mensagens automáticas
    Quando envia nova mensagem sem reautorização válida
    Então a mensagem pode ser encaminhada à equipe
    E o bloqueio de automação e follow-up permanece

  @C42 @RN08 @RN09
  Cenário: Redistribuir oportunidade após indisponibilidade do responsável
    Dado que o responsável de uma conversa ficou indisponível
    Quando o gestor atribui um vendedor elegível
    Então a nova responsabilidade fica visível e registrada
    E o histórico é preservado e a IA não retoma por causa da troca

  @C43 @RN05 @RN12
  Cenário: Evitar regressão causada por mensagem atrasada
    Dado que uma informação mais recente já corrigiu a necessidade do lead
    Quando chega uma mensagem anterior com a necessidade antiga
    Então ela não substitui o dado atual como se fosse uma nova correção
    E o histórico mantém contexto suficiente para revisão

  @C44 @RN02 @RN15
  Cenário: Comunicar automação sem expor credenciais
    Dado que um lead inicia atendimento com o agente
    Quando recebe a apresentação do atendimento
    Então consegue reconhecer que é um atendimento automatizado e como pedir humano
    E nenhuma credencial ou instrução interna é exposta

  @C45 @RN09
  Cenário: Retomar a IA por decisão explícita
    Dado que uma conversa está em atendimento humano
    E o agente está ativo e não há bloqueio de contato ou encerramento
    Quando uma pessoa autorizada devolve a conversa à IA
    Então a elegibilidade é reavaliada e a mudança fica registrada
    E agendamentos antigos cancelados não são reativados

  @C46 @RN13
  Cenário: Recusar condição comercial não autorizada
    Dado que não existe autorização para o desconto solicitado
    Quando o lead insiste que o agente confirme essa condição
    Então o agente não concede nem confirma o desconto
    E encaminha a solicitação de exceção à equipe com contexto
```

## 13. Critérios de aceite do produto

### 13.1 Roteiro de demonstração

1. Gestor cria conta e empresa, configura agente, conhecimento, produtos e vendedores pelo aplicativo.
2. Conecta Telegram, verifica prontidão e ativa o atendimento.
3. Lead fictício pergunta sobre a oferta, informa necessidades e recebe resposta sustentada no conhecimento da empresa.
4. Gestor visualiza o registro, histórico, classificação, evidências e próximo passo no CRM.
5. Uma conversa elegível recebe follow-up; outra responde antes do horário e comprova cancelamento.
6. Lead solicita humano; vendedor assume com contexto, responde pelo aplicativo e confirma ausência de resposta concorrente da IA.
7. Uma transferência sem vendedor disponível permanece visível até atribuição pelo gestor.
8. Gestor desativa o agente e comprova que novas saídas automáticas são impedidas.
9. Em M2, repete as decisões comerciais essenciais no WhatsApp sem recadastrar o negócio.
10. Repete perguntas em uma segunda empresa fictícia e demonstra personalização sem compartilhamento de dados.
11. Simula falha de canal, envio incerto e reentrega, mostrando estado, retomada e ausência de duplicação indevida.

### 13.2 Condições de aprovação

- **Aceite de negócio [P]:** histórias e regras necessárias a M1/M2 cobertas por evidências; todos os cenários obrigatórios aprovados para o marco correspondente.
- **Impedimentos:** vazamento entre empresas, mensagem comercial sem fonte, ação automática após bloqueio confirmado, duplicação indevida, perda de contexto ou encaminhamento invisível impedem aceite.
- **Pendências:** decisões V01–V07 que afetem o marco devem estar resolvidas ou ter redução de escopo explicitamente aprovada. V08 deve ser resolvida antes do piloto real; V09 antes de aceitar a política comercial; V10 antes de incluir voz.
- **Evidência mínima:** cenário, dados sintéticos, configuração, canal, versão avaliada, resultado esperado/observado e responsável pela validação. Distinguir aprovado, reprovado, bloqueado e não executado.
- **Conclusão do ciclo:** exige M1 e M2. Se houver somente Telegram, registrar conclusão parcial e pendência multicanal.

## 14. Decisões para validação e preparação da SPEC

| ID | Decisão em aberto | Proposta ou encaminhamento | Responsável sugerido |
| --- | --- | --- | --- |
| V01 | Viabilidade da criação self-service do bot Telegram | Validar a experiência descrita nas fontes; alternativa manual é contingência de teste, não aceite silencioso | Produto + responsável técnico |
| V02 | Segmento demonstrativo e prontidão mínima | Escolher um negócio fictício principal, catálogo e fonte comercial; validar campos obrigatórios e responsável de contingência | Produto + representante comercial |
| V03 | Rubrica de qualificação e score | Aprovar classificações, evidências e limiares; usar categorias antes de inventar escala numérica | Gestor comercial + Produto |
| V04 | Follow-up e opt-out | Definir quantidade, intervalo, validade, fuso, horários, reautorização e compatibilidade com a restrição inbound das fontes | Produto + gestor comercial |
| V05 | Operação humana | Aprovar habilitação de vendedores, permissões, seleção/atribuição, disponibilidade, responsável da fila e prazo de tratamento | Produto + operação |
| V06 | Documentos e mídias | Definir formatos e tamanhos da base; confirmar texto obrigatório e tratamento de mensagens não suportadas | Produto + responsável técnico |
| V07 | Política de dados para piloto | Definir transparência, retenção, exclusão, acesso e responsáveis antes de usar dados reais | Responsável pelo produto + responsável por privacidade |
| V08 | Metas, volume, custo e piloto | Definir amostra, duração, baseline manual, latência aceitável, concorrência, orçamento e critério de continuidade | Produto + operação |
| V09 | Atualização e conflito de fontes comerciais | Aprovar quais fontes são autoritativas e como o gestor resolve divergências; até lá, não escolher uma afirmação conflitante | Gestor comercial |
| V10 | Inclusão de voz | Avaliar viabilidade e custo após proteger M1/M2; aprovar critérios próprios antes de incluir | Produto + responsável técnico |

**Decisões de produto propostas neste PRD:** estados separados; qualificação por evidências; fila humana sem abandono; precedência do controle humano; follow-up limitado e cancelável; nenhuma fusão automática entre canais; falhas com saída operacional explícita. Essas propostas precisam ser validadas, não tratadas como decisões já tomadas pelo solicitante.

**Decisões técnicas adiadas:** arquitetura, módulos, modelo de dados, APIs, contratos entre canais, autenticação concreta, tecnologias de IA, estratégia de processamento de documentos, mecanismo de agendamento, infraestrutura, execução de testes e deploy. A SPEC deverá referenciar os IDs aprovados e demonstrar como satisfazê-los sem alterar o comportamento comercial.

## 15. Rastreabilidade e registro desta versão

| Grupo | Histórias | Regras | Cenários principais | Fontes |
| --- | --- | --- | --- | --- |
| Configuração e acesso | US-01–13, US-34 | RN-01–03, RN-15 | C01–07, C26–27, C44 | F01 §§6, 14, 19, 24; F02 §8; F03 §1 |
| Conhecimento e conversa | US-05–07, US-14–20 | RN-04–05 | C08–14, C17–20, C43 | F01 §§7, 11–13, 22–23; F03 §3 |
| Qualificação e CRM | US-08, US-23, US-26–29, US-33, US-35 | RN-06–07 | C14–16, C23, C28–30, C37 | F01 §§6, 9, 21 |
| Encaminhamento e controle | US-19, US-23–25, US-30 | RN-08–09, RN-13 | C21–30, C42, C45–46 | F01 §§9–10 |
| Acompanhamento e recuperação | US-18, US-21–22, US-31–32 | RN-10–12 | C31–38, C41, C43 | F01 §§6, 24; F02 §6; F03 fases 4, 8 |
| Multicanal, proteção e avaliação | US-34, US-36–38 | RN-01, RN-14–15 | C02, C20, C39–40, C44 | F01 §§14, 24, 27; F02 §§4–8 |

**Verificações desta elaboração:** leitura das três fontes em `docs`, incluindo imagens da ideação; inspeção do contexto, regras e estado local do Git; revisão de precedência, cobertura e consistência interna do PRD. Não foram executados testes de aplicação, simulações de canais ou validações com clientes. A abrangência da validação foi confirmada pelo solicitante; a aprovação integral do produto permanece pendente.

**Próximo marco:** validar o PRD e suas decisões pendentes; depois elaborar a SPEC. Este arquivo é a entrega local solicitada em `doc-spec/PRD-v1.md`; não representa publicação no rastreador de issues nem autorização para iniciar implementação.
