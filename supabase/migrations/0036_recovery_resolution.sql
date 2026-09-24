ALTER TABLE app.delivery_incidents ADD COLUMN resolution_evidence text,
  ADD COLUMN resolved_at timestamptz, ADD COLUMN resolved_by uuid,
  ADD CONSTRAINT delivery_incident_resolver_same_org FOREIGN KEY (organization_id, resolved_by)
    REFERENCES app.org_members(organization_id, user_id) ON DELETE RESTRICT;

CREATE FUNCTION private.resolve_delivery_incident(
  p_org uuid, p_incident uuid, p_evidence text
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_intent app.outbound_intents%ROWTYPE; v_incident app.delivery_incidents%ROWTYPE;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) OR
     length(trim(p_evidence)) < 10 OR length(p_evidence) > 1000 THEN
    RAISE EXCEPTION 'resolution forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_incident FROM app.delivery_incidents d
    WHERE d.organization_id = p_org AND d.id = p_incident;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'incident not found' USING ERRCODE = 'P0002';
  END IF;
  SELECT * INTO v_intent FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = v_incident.intent_id;
  PERFORM 1 FROM app.conversations c WHERE c.organization_id = p_org
    AND c.id = v_intent.conversation_id FOR UPDATE;
  PERFORM 1 FROM app.outbound_intents i WHERE i.organization_id = p_org
    AND i.id = v_intent.id FOR UPDATE;
  SELECT * INTO v_incident FROM app.delivery_incidents d
    WHERE d.organization_id = p_org AND d.id = p_incident FOR UPDATE;
  IF v_incident.state = 'resolved' THEN
    RETURN 'resolved';
  END IF;
  IF v_intent.status <> 'unknown' THEN
    RAISE EXCEPTION 'incident not uncertain' USING ERRCODE = '23514';
  END IF;
  UPDATE app.delivery_incidents d SET state = 'resolved', resolution_evidence = trim(p_evidence),
    resolved_at = now(), resolved_by = private.actor_id()
    WHERE d.organization_id = p_org AND d.id = p_incident;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'delivery_incident.resolved');
  RETURN 'resolved';
END $$;
ALTER FUNCTION private.resolve_delivery_incident(uuid,uuid,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.resolve_delivery_incident(uuid,uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.resolve_delivery_incident(uuid,uuid,text) TO app_api;
