-- Managed Telegram bot provisioning. Tokens are encrypted by the API before persistence.
CREATE TABLE app.telegram_provisioning (
  organization_id uuid PRIMARY KEY REFERENCES app.organizations(id) ON DELETE RESTRICT,
  request_hash text NOT NULL UNIQUE,
  request_ciphertext text NOT NULL,
  telegram_owner_id bigint UNIQUE,
  bot_id bigint UNIQUE,
  bot_username text,
  token_ciphertext text,
  webhook_secret_ciphertext text,
  webhook_secret_hash text UNIQUE,
  status text NOT NULL DEFAULT 'awaiting_owner'
    CHECK (status IN ('awaiting_owner', 'awaiting_bot', 'configuring', 'connected', 'failed')),
  failure_code text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (token_ciphertext IS NULL OR bot_id IS NOT NULL),
  CHECK (status <> 'connected' OR
    (bot_id IS NOT NULL AND webhook_secret_hash IS NOT NULL))
);
CREATE INDEX telegram_provisioning_owner_pending
  ON app.telegram_provisioning(telegram_owner_id)
  WHERE status IN ('awaiting_bot', 'configuring');

-- The inbox is independent of AI/sender. A sealed batch can be consumed once.
CREATE TABLE app.telegram_message_buffer (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  bot_id bigint NOT NULL REFERENCES app.telegram_provisioning(bot_id) ON DELETE RESTRICT,
  chat_id bigint NOT NULL,
  telegram_message_id bigint NOT NULL,
  body text NOT NULL CHECK (length(body) BETWEEN 1 AND 8000),
  received_at timestamptz NOT NULL DEFAULT now(),
  batch_id uuid,
  UNIQUE (bot_id, chat_id, telegram_message_id),
  UNIQUE (organization_id, id)
);
CREATE INDEX telegram_buffer_open
  ON app.telegram_message_buffer(bot_id, chat_id, received_at, id)
  WHERE batch_id IS NULL;

CREATE TABLE app.telegram_message_batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  bot_id bigint NOT NULL REFERENCES app.telegram_provisioning(bot_id) ON DELETE RESTRICT,
  chat_id bigint NOT NULL,
  body text NOT NULL,
  status text NOT NULL DEFAULT 'ready'
    CHECK (status IN ('ready', 'processing', 'processed', 'failed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id)
);
ALTER TABLE app.telegram_message_buffer ADD CONSTRAINT telegram_buffer_batch_org
  FOREIGN KEY (organization_id, batch_id)
  REFERENCES app.telegram_message_batches(organization_id, id) ON DELETE RESTRICT;

ALTER TABLE app.telegram_provisioning ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.telegram_provisioning FORCE ROW LEVEL SECURITY;
ALTER TABLE app.telegram_message_buffer ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.telegram_message_buffer FORCE ROW LEVEL SECURITY;
ALTER TABLE app.telegram_message_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.telegram_message_batches FORCE ROW LEVEL SECURITY;

CREATE POLICY telegram_provisioning_manager ON app.telegram_provisioning TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)))
  WITH CHECK (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY telegram_buffer_manager ON app.telegram_message_buffer FOR SELECT TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY telegram_batches_manager ON app.telegram_message_batches FOR SELECT TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));

-- Webhook endpoints are authenticated before entering these functions. Direct table
-- writes remain restricted to a zero-actor transaction used by trusted ingress.
CREATE POLICY telegram_provisioning_ingress ON app.telegram_provisioning TO app_api
  USING ((SELECT private.actor_id()) = '00000000-0000-0000-0000-000000000000'::uuid)
  WITH CHECK ((SELECT private.actor_id()) = '00000000-0000-0000-0000-000000000000'::uuid);
CREATE POLICY telegram_buffer_ingress ON app.telegram_message_buffer TO app_api
  USING ((SELECT private.actor_id()) = '00000000-0000-0000-0000-000000000000'::uuid)
  WITH CHECK ((SELECT private.actor_id()) = '00000000-0000-0000-0000-000000000000'::uuid);
CREATE POLICY telegram_batches_ingress ON app.telegram_message_batches TO app_api
  USING ((SELECT private.actor_id()) = '00000000-0000-0000-0000-000000000000'::uuid)
  WITH CHECK ((SELECT private.actor_id()) = '00000000-0000-0000-0000-000000000000'::uuid);
CREATE POLICY telegram_buffer_worker ON app.telegram_message_buffer TO app_worker
  USING (true) WITH CHECK (true);
CREATE POLICY telegram_batches_worker ON app.telegram_message_batches TO app_worker
  USING (true) WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE ON app.telegram_provisioning TO app_api;
GRANT SELECT, INSERT, UPDATE ON app.telegram_message_buffer TO app_api;
GRANT SELECT, INSERT, UPDATE ON app.telegram_message_batches TO app_api;
GRANT SELECT, UPDATE ON app.telegram_message_buffer TO app_worker;
GRANT SELECT, INSERT ON app.telegram_message_batches TO app_worker;
