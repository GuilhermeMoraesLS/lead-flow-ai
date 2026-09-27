-- A durable claim per inbound message prevents repeated provider calls and effects.
CREATE TABLE app.catalog_agent_runs (
  organization_id uuid NOT NULL,
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL,
  message_id uuid NOT NULL,
  intent_id uuid,
  status text NOT NULL CHECK (status IN ('running', 'pending', 'handoff', 'failed')),
  model text NOT NULL,
  prompt_version text NOT NULL,
  commercial_revision bigint NOT NULL CHECK (commercial_revision > 0),
  input_tokens integer CHECK (input_tokens >= 0),
  output_tokens integer CHECK (output_tokens >= 0),
  estimated_cost_usd numeric(12,6) CHECK (estimated_cost_usd >= 0),
  failure_code text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, conversation_id, message_id),
  FOREIGN KEY (organization_id, conversation_id)
    REFERENCES app.conversations(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, message_id)
    REFERENCES app.messages(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, intent_id)
    REFERENCES app.outbound_intents(organization_id, id) ON DELETE RESTRICT
);

ALTER TABLE app.catalog_agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.catalog_agent_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY catalog_runs_manager_read ON app.catalog_agent_runs FOR SELECT TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY catalog_runs_manager_insert ON app.catalog_agent_runs FOR INSERT TO app_api
  WITH CHECK (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY catalog_runs_manager_update ON app.catalog_agent_runs FOR UPDATE TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)))
  WITH CHECK (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
GRANT SELECT, INSERT ON app.catalog_agent_runs TO app_api;
GRANT UPDATE (intent_id, status, input_tokens, output_tokens, estimated_cost_usd,
  failure_code, updated_at) ON app.catalog_agent_runs TO app_api;
