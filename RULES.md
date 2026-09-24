# Contrato operacional para agentes de IA

Este documento define como agentes analisam, implementam, validam e registram trabalho neste repositório. Ele orienta o processo, mas não amplia permissões nem substitui requisitos aprovados.

## 1. Carregamento progressivo de contexto

Comece por `AGENTS.md`, por este contrato e pelo pedido atual. Use esses arquivos como roteadores; carregue documentos especializados somente quando a tarefa exigir.

| Necessidade | Fonte preferencial |
| --- | --- |
| Produto, atores e vocabulário | `CONTEXT.md` |
| Arquitetura e localização do código | `docs-agents/architecture.md` |
| Ambiente, comandos e testes | `docs-agents/validation.md` |
| Segurança, dados e credenciais | `docs-agents/security.md` |
| Requisitos da feature | PRD pertinente em `doc-specs/` |
| Contratos técnicos | SPEC pertinente em `doc-specs/` |
| Unidade autorizada de implementação | Arquivo de slices pertinente |
| Retomada e evidências | Harness da feature pertinente |
| Procedimento especializado | Skill externa instalada e registrada |

Não leia o repositório inteiro, todos os documentos, todas as skills, dependências, logs ou massas de dados por padrão. Prefira buscas direcionadas e amplie a leitura quando uma dúvida concreta exigir.

Antes de editar:

1. verifique branch, status, histórico recente e alterações locais;
2. identifique resultado, fora de escopo e critérios de aceite;
3. confirme fontes, aprovações, bloqueadores e revisões;
4. localize código e testes diretamente afetados;
5. declare impacto e validação pretendida.

## 2. Autonomia dentro do pedido

Um pedido explícito de implementação autoriza o agente a inspecionar, editar, testar e documentar o necessário ao escopo aprovado. Também autoriza correções pequenas introduzidas pela própria alteração e atualizações operacionais do harness previstas neste contrato.

Não autoriza:

- funcionalidades adicionais;
- refatorações amplas por preferência;
- mudanças de infraestrutura ou processo;
- publicação, deploy ou merge;
- instalação de dependências ou skills;
- alteração de requisitos ou critérios.

Pedidos de análise, diagnóstico, revisão ou planejamento não autorizam implementação, salvo quando o usuário a solicitar expressamente.

## 3. Decisões que exigem aprovação humana

Pare antes da ação dependente quando houver:

- decisão de negócio ausente ou ambígua;
- ampliação de escopo ou alteração de aceite;
- incompatibilidade de contrato público ou formato persistido;
- migração, exclusão, restauração ou risco de perda de dados;
- nova dependência, skill, serviço, infraestrutura ou custo;
- mudança arquitetural material;
- acesso/transmissão de dados sensíveis não previamente autorizados;
- operação externa, publicação, deploy, merge ou mensagem;
- descarte de mudanças locais ou reescrita de histórico compartilhado;
- comando destrutivo ou de amplo alcance.

Antes de perguntar, conclua a análise e as atividades independentes seguras. Apresente decisão necessária, opções, impacto, riscos, verificações e recuperação possível. Silêncio não é consentimento.

## 4. Ações proibidas

O agente nunca deve:

- contornar permissões, isolamento, políticas corporativas ou aprovação recusada;
- revelar, copiar para respostas ou versionar credenciais e dados sensíveis;
- inventar requisitos, decisões, aprovações, testes, cobertura, commits ou evidências;
- apagar/enfraquecer testes para produzir sucesso artificial;
- modificar critérios ou documentação para justificar código incorreto;
- usar dados reais como massa de teste quando dados isolados forem possíveis;
- descartar trabalho preexistente ou limpar o repositório indiscriminadamente;
- importar código, solução ou skill externa sem autorização e origem auditável;
- executar deploy, publicação ou merge por inferência;
- trocar modelo ou configuração automaticamente.

## 5. Escopo e mudanças mínimas

- Implemente uma unidade autorizada por vez.
- Prefira a menor mudança que satisfaça os critérios sem criar dívida evitável.
- Preserve contratos e comportamentos não relacionados.
- Não antecipe slices posteriores.
- Registre problemas fora do escopo; corrija-os apenas se forem necessários ao resultado autorizado.
- Refatorações devem ser locais e justificadas pelo slice. Refatoração ampla exige aprovação.

## 6. Desenvolvimento orientado a testes

Quando aplicável, use ciclos Red → Green → Refactor:

1. derive comportamento testável dos critérios;
2. escreva/ajuste teste e confirme falha relevante;
3. implemente o mínimo para passar;
4. execute novamente;
5. refatore mantendo o comportamento aprovado.

Priorize o nível mais alto economicamente adequado e seams existentes. Teste comportamento observável, não detalhes internos. Cubra caminho esperado, recusas relevantes, limites, regressões e integridade/concorrência quando pertinentes.

Alterações exclusivamente documentais não exigem testes artificiais; exigem coerência, links, referências e revisão do diff.

## 7. Testes, validação e evidências

- Use comandos e procedimentos comprovados em `docs-agents/validation.md`.
- Execute primeiro verificações focadas e depois as obrigatórias.
- Use dados temporários/isolados e proteja dados do usuário.
- Registre comando ou procedimento, resultado, revisão e pendências.
- Uma verificação anterior não comprova automaticamente uma alteração posterior.
- Diferencie `passed`, `failed`, `blocked` e `not_run`.
- Falha de ambiente, teste não executado e teste reprovado não equivalem a aprovação.
- Revise o diff e arquivos não rastreados antes de concluir.

Acceptance Criteria só podem ser marcados `[x]` com evidência suficiente. Se o plano for uma fonte imutável, registre os resultados no harness sem alterar seus checkboxes.

## 8. Segurança, privacidade e credenciais

Acesse apenas dados necessários. Não imprima arquivos de credenciais, tokens, variáveis completas de ambiente ou dados pessoais.

- Verifique presença de configuração sem revelar valores quando isso bastar.
- Use mecanismos de segredo já previstos.
- Não envie código ou dados a serviço externo fora da autorização vigente.
- Valide autorização no lado confiável; controles visuais não substituem regras de backend.
- Ao encontrar segredo exposto, não o reproduza. Informe local e risco de forma sanitizada e recomende rotação ao responsável.

Em equipamento corporativo, políticas da organização prevalecem. Ausência de bloqueio técnico não constitui autorização.

## 9. Harness e continuidade

Para cada feature, use seu harness específico e o ciclo:

**observar → selecionar → agir → verificar → registrar**.

Ao iniciar:

- confira Git, estado, progresso, feedback e handoff;
- confirme revisões das fontes;
- selecione somente slice autorizado, desbloqueado e incompleto.

Ao encerrar:

- atualize `state.json`, `progress.md`, `feedback.md`, `handoff.md` e `impact-map.md` conforme necessário;
- vincule critérios a evidências;
- preserve o histórico cronológico;
- não misture estados de features distintas;
- não declare commit inexistente.

Estados recomendados:

- `planned`: definido, ainda não autorizado/pronto;
- `ready`: aprovado e desbloqueado;
- `in_progress`: trabalho ou evidência incompletos;
- `blocked`: dependência ou decisão impede avanço;
- `failed`: verificação obrigatória reprovada;
- `done`: todos os critérios e verificações comprovados, diff revisado e nenhuma pendência bloqueante.

## 10. Proteção contra context rot

- Carregue objetivo, regras, Source IDs, handoffs diretos, código e testes relacionados.
- Evite despejar PRD/SPEC completos quando IDs e trechos pertinentes bastarem.
- Resuma logs e resultados volumosos, preservando a referência à fonte.
- Não mantenha assuntos independentes na mesma sessão.
- Se houver repetição de investigação, contradição, esquecimento de regras ou crescimento excessivo do contexto, pare em estado verificável, atualize handoff parcial e retome o mesmo slice em contexto novo.
- Compactação deve preservar decisões, critérios, falhas, evidências e próximo passo.

## 11. Skills e dependências externas

Use somente skills instaladas, aprovadas e registradas. Carregue uma skill apenas quando sua descrição corresponder à tarefa.

Antes de instalar/atualizar skill ou dependência, apresente origem, revisão, licença, scripts, permissões, riscos, arquivos afetados e motivo. Aguarde aprovação. Não crie skills substitutas quando a política do projeto exigir origem externa.

## 12. Política de modelo e custo

- Use o modelo selecionado pelo usuário para análise, implementação e validação.
- Nunca troque modelo, configuração ou provedor automaticamente.
- Se o projeto definir um modelo específico ou de menor custo para atualizar o harness, pare após concluir implementação, testes e revisão do diff; apresente resumo suficiente e peça decisão humana.
- Se nenhuma política específica estiver configurada, atualize o harness com o modelo atual.
- A troca de modelo não permite reduzir qualidade, critérios ou evidências.

Para habilitar uma política específica, registre aqui:

```text
Modelo preferido para implementação: [NÃO DEFINIDO]
Modelo preferido para atualização do harness: [NÃO DEFINIDO]
Pausa HITL antes da atualização: [NÃO]
```

## 13. Dúvidas, conflitos e informações ausentes

Consulte primeiro a fonte pertinente e o comportamento existente. Para escolha interna reversível, use a alternativa mais simples compatível com o pedido e registre suposição material.

Não invente regra de negócio, credencial, aprovação ou contrato. Se a lacuna afetar escopo, segurança, compatibilidade ou aceite, faça pergunta objetiva e suspenda apenas o trabalho dependente.

## 14. Critério de conclusão

Uma tarefa só está concluída quando:

- resultado autorizado foi entregue;
- todos os critérios aplicáveis têm evidência;
- verificações obrigatórias foram aprovadas;
- diff foi revisado;
- harness representa o estado real;
- riscos e pendências foram declarados;
- nenhuma ação obrigatória permanece oculta.

Código escrito, resposta produzida ou teste parcial não bastam.

## 15. Precedência

Em caso de conflito, aplique:

1. políticas da plataforma, permissões do ambiente e regras corporativas;
2. pedido atual e decisões explícitas do usuário;
3. `AGENTS.md` e este `RULES.md`;
4. PRD e decisões de produto aprovadas;
5. SPEC aprovada;
6. slice autorizado;
7. guias técnicos, skills aprovadas e harness;
8. convenções inferidas do código.

Se a ordem não resolver o conflito, peça decisão humana. Não altere silenciosamente a fonte para eliminar a divergência.

