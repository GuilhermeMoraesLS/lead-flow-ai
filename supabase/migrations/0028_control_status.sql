CREATE TABLE app.control_operations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  conversation_id uuid,
  actor_id uuid NOT NULL,
  kind text NOT NULL CHECK (kind IN ('global_pause', 'human_claim')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id),
  FOREIGN KEY (organization_id, conversation_id)
    REFERENCES app.conversations(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, actor_id)
    REFERENCES app.org_members(organization_id, user_id) ON DELETE RESTRICT
);
CREATE TABLE app.control_attempts (
  organization_id uuid NOT NULL,
  control_id uuid NOT NULL,
  intent_id uuid NOT NULL,
  PRIMARY KEY (organization_id, control_id, intent_id),
  FOREIGN KEY (organization_id, control_id)
    REFERENCES app.control_operations(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, intent_id)
    REFERENCES app.outbound_intents(organization_id, id) ON DELETE RESTRICT
);
CREATE INDEX control_attempts_intent ON app.control_attempts(organization_id, intent_id);
ALTER TABLE app.control_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.control_operations FORCE ROW LEVEL SECURITY;
ALTER TABLE app.control_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.control_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY control_operations_bootstrap ON app.control_operations TO app_bootstrap
  USING (true) WITH CHECK (true);
CREATE POLICY control_attempts_bootstrap ON app.control_attempts TO app_bootstrap
  USING (true) WITH CHECK (true);
GRANT SELECT, INSERT ON app.control_operations, app.control_attempts TO app_bootstrap;

CREATE FUNCTION private.record_control(
  p_org uuid, p_conversation uuid, p_kind text
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_id uuid;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR
     p_kind NOT IN ('global_pause', 'human_claim') OR
     (p_kind = 'global_pause' AND (p_conversation IS NOT NULL OR
       NOT private.gestor_of(p_org))) OR
     (p_kind = 'human_claim' AND (p_conversation IS NULL OR
       NOT EXISTS (SELECT 1 FROM app.conversations c WHERE c.organization_id = p_org
         AND c.id = p_conversation AND c.claimed_by = private.actor_id()))) THEN
    RAISE EXCEPTION 'control forbidden' USING ERRCODE = '42501';
  END IF;
  INSERT INTO app.control_operations(organization_id, conversation_id, actor_id, kind)
    VALUES (p_org, p_conversation, private.actor_id(), p_kind) RETURNING id INTO v_id;
  INSERT INTO app.control_attempts(organization_id, control_id, intent_id)
    SELECT p_org, v_id, i.id FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.kind = 'synthetic_auto'
      AND i.status = 'dispatching'
      AND (p_conversation IS NULL OR i.conversation_id = p_conversation);
  RETURN v_id;
END $$;
ALTER FUNCTION private.record_control(uuid,uuid,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.record_control(uuid,uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.record_control(uuid,uuid,text) TO app_api;

CREATE FUNCTION private.control_status(p_org uuid, p_control uuid)
RETURNS TABLE(completion text, prior_accepted boolean, rejected_count integer,
              unknown_count integer, pending_count integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_control app.control_operations%ROWTYPE; v_accepted integer;
  v_rejected integer; v_unknown integer; v_pending integer;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() THEN
    RAISE EXCEPTION 'control not found' USING ERRCODE = 'P0002';
  END IF;
  SELECT * INTO v_control FROM app.control_operations c
    WHERE c.organization_id = p_org AND c.id = p_control;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'control not found' USING ERRCODE = 'P0002';
  END IF;
  IF NOT private.gestor_of(p_org) AND v_control.actor_id IS DISTINCT FROM private.actor_id() THEN
    RAISE EXCEPTION 'control forbidden' USING ERRCODE = '42501';
  END IF;
  SELECT count(*) FILTER (WHERE i.status = 'accepted'),
         count(*) FILTER (WHERE i.status = 'rejected'),
         count(*) FILTER (WHERE i.status = 'unknown'),
         count(*) FILTER (WHERE i.status = 'dispatching')
    INTO v_accepted, v_rejected, v_unknown, v_pending
    FROM app.control_attempts ca JOIN app.outbound_intents i
      ON i.organization_id = ca.organization_id AND i.id = ca.intent_id
    WHERE ca.organization_id = p_org AND ca.control_id = p_control;
  RETURN QUERY SELECT CASE WHEN v_pending > 0 THEN 'pending_external_attempt'
    WHEN v_unknown > 0 THEN 'unknown' ELSE 'complete' END,
    v_accepted > 0, v_rejected, v_unknown, v_pending;
END $$;
ALTER FUNCTION private.control_status(uuid,uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.control_status(uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.control_status(uuid,uuid) TO app_api;
