ALTER TABLE app.leads
  ADD COLUMN stage text NOT NULL DEFAULT 'new'
    CHECK (stage IN ('new', 'in_service', 'qualified', 'handed_off', 'negotiating', 'won', 'lost'));

ALTER TABLE app.conversations
  ADD COLUMN mode text NOT NULL DEFAULT 'automatic'
    CHECK (mode IN ('automatic', 'awaiting_human', 'human')),
  ADD COLUMN assigned_seller_id uuid,
  ADD COLUMN claimed_by uuid,
  ADD COLUMN handoff_reason text,
  ADD COLUMN handoff_requested_at timestamptz,
  ADD COLUMN summary text,
  ADD COLUMN summary_status text NOT NULL DEFAULT 'not_requested'
    CHECK (summary_status IN ('not_requested', 'unavailable', 'ready')),
  ADD CONSTRAINT conversation_seller_same_org FOREIGN KEY (organization_id, assigned_seller_id)
    REFERENCES app.sellers(organization_id, id) ON DELETE RESTRICT,
  ADD CONSTRAINT conversation_claim_same_org FOREIGN KEY (organization_id, claimed_by)
    REFERENCES app.org_members(organization_id, user_id) ON DELETE RESTRICT;
CREATE INDEX conversations_assigned_seller ON app.conversations(organization_id, assigned_seller_id)
  WHERE assigned_seller_id IS NOT NULL;

CREATE TABLE app.operation_incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  conversation_id uuid NOT NULL,
  cause_event_id uuid NOT NULL,
  kind text NOT NULL CHECK (kind = 'human_handoff'),
  reason text NOT NULL,
  owner_member_id uuid NOT NULL,
  state text NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'resolved')),
  next_action text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id),
  UNIQUE (organization_id, cause_event_id),
  FOREIGN KEY (organization_id, conversation_id)
    REFERENCES app.conversations(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, cause_event_id)
    REFERENCES app.inbound_events(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, owner_member_id)
    REFERENCES app.org_members(organization_id, user_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX one_open_handoff_per_conversation
  ON app.operation_incidents(organization_id, conversation_id) WHERE state = 'open';
CREATE INDEX open_handoff_queue ON app.operation_incidents(organization_id, created_at, id)
  WHERE state = 'open';
ALTER TABLE app.operation_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.operation_incidents FORCE ROW LEVEL SECURITY;
CREATE POLICY incident_manager_read ON app.operation_incidents FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY incident_handoff ON app.operation_incidents TO app_bootstrap
USING (true) WITH CHECK (true);
GRANT SELECT ON app.operation_incidents TO app_api;
GRANT SELECT, INSERT ON app.operation_incidents TO app_bootstrap;

ALTER TABLE app.outbox_events DROP CONSTRAINT outbox_events_event_type_check;
ALTER TABLE app.outbox_events ADD CONSTRAINT outbox_events_event_type_check
  CHECK (event_type IN ('inbound.recorded', 'handoff.requested'));

CREATE FUNCTION private.request_human_from_test_event(
  p_channel uuid, p_token_hash text, p_external_event text
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_org uuid; v_event uuid; v_conversation uuid; v_mode text;
  v_owner uuid; v_incident uuid;
BEGIN
  SELECT c.organization_id INTO v_org FROM app.channels c
   WHERE c.id = p_channel AND c.token_hash = p_token_hash;
  IF v_org IS NULL THEN
    RAISE EXCEPTION 'invalid channel token' USING ERRCODE = '28000';
  END IF;
  SELECT e.id, e.conversation_id INTO v_event, v_conversation
    FROM app.inbound_events e
   WHERE e.organization_id = v_org AND e.channel_id = p_channel
     AND e.external_event_id = p_external_event AND e.event_type = 'message'
     AND e.processing_status = 'recorded'
   FOR UPDATE;
  IF v_event IS NULL OR v_conversation IS NULL THEN
    RAISE EXCEPTION 'recorded message required' USING ERRCODE = 'P0002';
  END IF;
  SELECT c.mode INTO v_mode FROM app.conversations c
   WHERE c.organization_id = v_org AND c.id = v_conversation FOR UPDATE;
  IF v_mode = 'awaiting_human' OR v_mode = 'human' THEN
    SELECT i.id INTO v_incident FROM app.operation_incidents i
     WHERE i.organization_id = v_org AND i.conversation_id = v_conversation
       AND i.state = 'open';
    RETURN v_incident;
  END IF;
  SELECT m.user_id INTO v_owner FROM app.org_members m
   WHERE m.organization_id = v_org AND m.role = 'gestor' AND m.status = 'active'
   ORDER BY m.created_at, m.user_id LIMIT 1;
  IF v_owner IS NULL THEN
    RAISE EXCEPTION 'no queue owner' USING ERRCODE = '42501';
  END IF;
  UPDATE app.conversations SET mode = 'awaiting_human',
    handoff_reason = 'explicit_request', handoff_requested_at = now(),
    summary_status = 'unavailable'
   WHERE organization_id = v_org AND id = v_conversation;
  UPDATE app.leads SET stage = 'handed_off'
   WHERE organization_id = v_org AND id = (
     SELECT c.lead_id FROM app.conversations c
     WHERE c.organization_id = v_org AND c.id = v_conversation
   );
  INSERT INTO app.operation_incidents(
    organization_id, conversation_id, cause_event_id, kind, reason,
    owner_member_id, next_action
  ) VALUES (
    v_org, v_conversation, v_event, 'human_handoff', 'explicit_request',
    v_owner, 'Atribuir manualmente a vendedor elegível.'
  ) RETURNING id INTO v_incident;
  INSERT INTO app.outbox_events(organization_id, event_type, aggregate_id, dedupe_key)
  VALUES (v_org, 'handoff.requested', v_conversation, 'handoff:' || v_event::text);
  INSERT INTO app.audit_events(organization_id, actor_id, action)
  VALUES (v_org, v_owner, 'handoff.requested');
  RETURN v_incident;
END $$;
ALTER FUNCTION private.request_human_from_test_event(uuid,text,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.request_human_from_test_event(uuid,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.request_human_from_test_event(uuid,text,text) TO app_api;
