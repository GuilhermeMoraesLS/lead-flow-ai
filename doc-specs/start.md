# Iniciar o projeto localmente

Execute os comandos abaixo na raiz do repositório, no PowerShell. É necessário ter Docker Desktop, o ambiente `.venv` e as dependências de `apps/web` já preparados (em um computador novo, siga primeiro a seção seguinte). Mantenha os terminais de API, web, worker, beat e túnel abertos durante o teste. A interface começa em `/entrar` (login) e `/cadastro` (nova conta e empresa).

## Instalação em um computador novo

### 1. Pré-requisitos (uma vez por máquina)

| Ferramenta | Versão | Instalação sugerida |
| --- | --- | --- |
| Git | qualquer recente | `winget install --id Git.Git` |
| Python | **3.14** (o código usa sintaxe exclusiva do 3.14) | `winget install --id Python.Python.3.14` |
| Node.js | **24.x** (exigido em `apps/web/package.json`) | `winget install --id OpenJS.NodeJS.LTS` e confira com `node --version` |
| Docker Desktop | qualquer recente | `winget install --id Docker.DockerDesktop` |
| ngrok | 3.20 ou superior | `winget install --id Ngrok.Ngrok --source winget` e depois `ngrok update` |

Depois de instalar, feche e reabra o terminal (no VS Code, reinicie o editor) para carregar o novo PATH.

### 2. Clonar e instalar dependências

```powershell
git clone https://github.com/GuilhermeMoraesLS/lead-flow-ai.git
cd lead-flow-ai
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
cd apps\web
npm ci
cd ..\..
```

### 3. Recriar os arquivos locais de configuração

A pasta `.local/` é ignorada pelo Git e não vem no clone. `.local/sl01.env` (senhas do banco, Redis e chave de criptografia) é gerado automaticamente pelo `prepare`. Crie os outros dois manualmente:

- `.local/telegram.env`

  ```
  TELEGRAM_MANAGER_USERNAME=LeadFlowAI_gestor_bot
  TELEGRAM_MANAGER_TOKEN=<token do bot gestor, obtido no @BotFather>
  TELEGRAM_PUBLIC_URL=https://<seu domínio estático>.ngrok-free.dev
  ```

  `TELEGRAM_MANAGER_WEBHOOK_SECRET` é gerado pelo comando `telegram-webhook`. Se o outro computador continuar em uso, copie o arquivo inteiro de lá por um meio seguro (pendrive, gerenciador de senhas), nunca pelo Git ou por chat: um segredo novo reregistra o bot gestor e desliga o webhook da máquina anterior.

- `.local/openai.env` (necessário para o atendimento D0)

  ```
  OPENAI_API_KEY=<sua chave da OpenAI>
  ```

### 4. Autenticar o ngrok

Use a mesma conta ngrok para manter o mesmo domínio estático:

```powershell
ngrok config add-authtoken <SEU_AUTHTOKEN>
```

No plano gratuito, o domínio só pode estar aberto em um computador por vez: encerre o túnel na outra máquina antes de abrir neste.

### 5. Subir o ambiente pela primeira vez

1. Abra o Docker Desktop e espere o status **Engine running**.
2. Prepare banco, autenticação e Redis, e aplique as migrations:

   ```powershell
   .venv\Scripts\python.exe scripts\local.py prepare
   .venv\Scripts\python.exe scripts\local.py migrate
   ```

3. Abra um terminal para cada serviço e deixe todos rodando:

   ```powershell
   .venv\Scripts\python.exe scripts\local.py api
   .venv\Scripts\python.exe scripts\local.py web
   .venv\Scripts\python.exe scripts\local.py worker
   .venv\Scripts\python.exe scripts\local.py beat
   .venv\Scripts\python.exe scripts\local.py tunnel
   ```

4. Com o túnel no ar, registre o webhook do bot gestor e **reinicie a API** se o comando tiver acabado de gerar o segredo:

   ```powershell
   .venv\Scripts\python.exe scripts\local.py telegram-webhook
   ```

5. Acesse http://127.0.0.1:3000, crie a conta em **Criar conta** e siga a **Jornada de ativação**.

O banco deste computador começa vazio: contas, produtos, vendedores e bots conectados no outro computador não são transferidos. Crie a conta e conecte um bot novamente pela tela **Telegram**.

### 6. Nas próximas vezes

Abra o Docker Desktop e suba os cinco terminais do passo 5.3. `prepare`, `migrate` e `telegram-webhook` só precisam ser repetidos se houver migrations novas no repositório (rode `migrate` após cada `git pull`) ou se `TELEGRAM_PUBLIC_URL` mudar.

## Preparar serviços e banco

```powershell
.venv\Scripts\python.exe scripts\local.py prepare
.venv\Scripts\python.exe scripts\local.py migrate
```

`prepare` inicia PostgreSQL, Supabase Auth e Redis locais com Docker. `migrate` aplica as migrations pendentes; pode ser repetido.

## Iniciar a aplicação

Abra um terminal para cada comando:

```powershell
.venv\Scripts\python.exe scripts\local.py api
.venv\Scripts\python.exe scripts\local.py web
.venv\Scripts\python.exe scripts\local.py worker
.venv\Scripts\python.exe scripts\local.py beat
```

A interface fica em `http://127.0.0.1:3000` e a API em `http://127.0.0.1:8000`. O worker executa tarefas duráveis; o beat agenda recuperação, fechamento do buffer após 5 segundos de silêncio e consumo dos lotes das empresas com D0 ativado.

## Expor a API para o Telegram em teste

A API é exposta por um domínio estático do ngrok, que não muda entre reinícios. Os webhooks são registrados uma vez e continuam válidos.

### Configuração única

1. Instale e atualize o ngrok (`winget install --id Ngrok.Ngrok --source winget` e depois `ngrok update`; o pacote do winget vem em versão antiga, sem a flag `--url`) e crie uma conta gratuita em https://dashboard.ngrok.com.
2. Autentique o ngrok com o authtoken do painel (Your Authtoken). Rode o comando você mesmo; nunca coloque o token em arquivos versionados, commits ou mensagens:

   ```powershell
   ngrok config add-authtoken <SEU_AUTHTOKEN>
   ```

3. No painel, em **Domains**, reivindique o domínio estático gratuito (ex.: `seu-nome.ngrok-free.app`).
4. Em `.local/telegram.env` (ignorado pelo Git), defina `TELEGRAM_PUBLIC_URL=https://seu-nome.ngrok-free.app`. O arquivo também deve conter `TELEGRAM_MANAGER_USERNAME` e `TELEGRAM_MANAGER_TOKEN`.
5. Com o túnel no ar (próxima seção), registre o webhook do bot gestor:

   ```powershell
   .venv\Scripts\python.exe scripts\local.py telegram-webhook
   ```

   Na primeira execução, o comando gera `TELEGRAM_MANAGER_WEBHOOK_SECRET` no arquivo local. **Reinicie a API depois disso** para carregar o segredo.
6. Se já havia um bot de teste conectado por uma URL antiga, aponte-o uma última vez para o domínio fixo:

   ```powershell
   .venv\Scripts\python.exe .local\refresh_test_bot_webhook.py
   ```

   Bots conectados depois disso já nascem com o domínio fixo.

### A cada sessão de teste

Em outro terminal, mantenha o túnel aberto junto com API, worker e beat:

```powershell
.venv\Scripts\python.exe scripts\local.py tunnel
```

O comando usa exatamente o domínio de `TELEGRAM_PUBLIC_URL`. Não é preciso registrar os webhooks de novo. Enquanto o túnel ou a API estiverem parados, o Telegram guarda as atualizações e reenvia por tempo limitado.

## Roteiro D0

1. No app, crie ou retome uma operação de teste, salve as instruções do agente e cadastre ao menos um produto sintético disponível. Conecte o bot da operação, se ainda não estiver conectado.
2. Confirme que o túnel (`scripts\local.py tunnel`) está no ar. Os webhooks só precisam ser registrados de novo se `TELEGRAM_PUBLIC_URL` mudar: o bot gestor usa `scripts/local.py telegram-webhook`; os bots já conectados usam `.venv\Scripts\python.exe .local\refresh_test_bot_webhook.py`, que atualiza todos os bots com status conectado no banco local.
3. No painel “Bot Telegram da sua empresa”, clique em **Ativar atendimento D0**. A ativação é separada da prontidão geral do agente. Mensagens recebidas antes dela não disparam resposta retroativa.
4. De uma conta Telegram de teste, envie em chat privado uma pergunta contendo exatamente o nome do produto disponível. Aguarde mais de cinco segundos e use **Atualizar conversas**. Abra o histórico para conferir entrada, resposta e estado `accepted`.
5. Repita com produto ausente e pedido humano; confira a fila e a ausência de resposta inventada. Teste pausa/opt-out antes de nova pergunta e confira que não há novo envio. Para reentrega e envio incerto, use os testes de integração locais; não provoque falha de rede em uma conversa real sem controle da tentativa.

O painel de lotes mostra modelo, revisão do catálogo e custo estimado quando houve chamada ao modelo. Registre horário, configuração sintética, texto esperado/observado e estado de entrega ao executar a prova real. O domínio do ngrok só responde enquanto esta máquina e o túnel estão ligados. D0 não conclui M1/M2, C01/V01 integrais nem a avaliação ampla do modelo.
