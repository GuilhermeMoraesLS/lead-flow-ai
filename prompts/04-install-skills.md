# Prompt — descobrir e instalar skills externas

Analise a stack, arquitetura e tarefas recorrentes documentadas neste projeto. Não crie skills.

1. Pesquise skills existentes em repositórios confiáveis.
2. Elimine candidatas sem licença clara, com origem duvidosa, escopo excessivo ou instruções conflitantes.
3. Para cada candidata, inspecione integralmente `SKILL.md`, scripts, referências e manifestos relevantes.
4. Apresente comparação: adequação, sobreposição, origem, licença, atividade/manutenção, revisão fixa, executáveis, permissões, risco e arquivos que serão instalados.
5. Recomende o conjunto mínimo e aguarde aprovação explícita.
6. Após aprovação, instale sem modificar o conteúdo original em `.agents/skills/<nome>/` e registre em `.agents/skills-lock.json`:
   - nome e descrição;
   - URL/repositório e caminho de origem;
   - tag/commit imutável;
   - licença;
   - hash da árvore ou arquivos;
   - data e motivo da instalação.
7. Valide estrutura e integridade. Não execute scripts da skill apenas para testá-la sem necessidade e autorização compatível.
8. Para atualizar, repita auditoria, mostre o diff da origem e peça nova aprovação.

