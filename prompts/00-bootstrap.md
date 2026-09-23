# Prompt mestre — iniciar qualquer projeto

Analise este repositório e prepare o contexto para desenvolvimento assistido por agentes.

Objetivo: preencher/adaptar `AGENTS.md`, `RULES.md`, `CONTEXT.md`, `docs-agents/`, `doc-specs/`, `.agents/harness/`, `.agents/skills/` e `.agents/skills-lock.json` usando apenas evidências reais.

Regras:

1. Verifique branch, Git, documentação, manifestos e comandos existentes. Preserve alterações locais.
2. Use divulgação progressiva: `AGENTS.md` é um índice curto; detalhes ficam em guias temáticos.
3. Faça buscas direcionadas; não carregue o repositório inteiro.
4. Não invente comandos, arquitetura, requisitos ou aprovações. Use `[A DEFINIR]`.
5. Não implemente comportamento do produto nesta tarefa.
6. Não crie skills. Pesquise apenas skills existentes em repositórios públicos/confiáveis que correspondam à stack e aos fluxos comprovados.
7. Antes de baixar qualquer skill, apresente uma tabela com: nome, finalidade, repositório, caminho, mantenedor, licença, revisão fixa, scripts/executáveis, permissões e risco. Aguarde aprovação explícita.
8. Após aprovação, baixe somente a pasta necessária, fixe commit/tag, preserve `SKILL.md` e recursos originais sem editar e registre tudo em `.agents/skills-lock.json`, incluindo hash de integridade.
9. Se nenhuma skill adequada existir, deixe a necessidade registrada; não crie uma substituta.
10. Inicialize o harness a partir de specs/slices aprovados. Ausência de aprovação gera estado planejado/bloqueado, nunca concluído.
11. Valide links, JSON, caminhos, provenance das skills e coerência dos índices.

Primeiro apresente descobertas, plano de arquivos e propostas de skills. Continue com arquivos documentais reversíveis; pause somente a instalação das skills e decisões que alterem materialmente o resultado.

