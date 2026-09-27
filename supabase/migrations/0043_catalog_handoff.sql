CREATE FUNCTION private.handoff_catalog_reply(
  p_org uuid, p_conversation uuid, p_message uuid, p_input_revision integer, p_reason text
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_conversation app.conversations%ROWTYPE;
  v_event uuid; v_owner uuid; v_incident uuid; v_latest uuid;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org)
    OR p_reason NOT IN ('catalog_unsupported', 'catalog_conflict',
      'provider_unavailable', 'catalog_invalid', 'commercial_exception', 'sensitive_request') THEN
    RAISE EXCEPTION 'handoff forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_conversation FROM app.conversations c
    WHERE c.organization_id = p_org AND c.id = p_conversation FOR UPDATE;
  IF NOT FOUND OR v_conversation.input_revision IS DISTINCT FROM p_input_revision THEN
    RAISE EXCEPTION 'conversation changed' USING ERRCODE = '40001';
  END IF;
  SELECT m.id INTO v_latest FROM app.messages m
    WHERE m.organization_id = p_org AND m.conversation_id = p_conversation
    ORDER BY m.received_at DESC, m.id DESC LIMIT 1;
  IF v_latest IS DISTINCT FROM p_message THEN
    RAISE EXCEPTION 'message changed' USING ERRCODE = '40001';
  END IF;
  SELECT i.id INTO v_incident FROM app.operation_incidents i
    WHERE i.organization_id = p_org AND i.conversation_id = p_conversation
      AND i.state = 'open';
  IF v_incident IS NOT NULL THEN RETURN v_incident; END IF;
  SELECT e.id INTO v_event FROM app.inbound_events e
    WHERE e.organization_id = p_org AND e.conversation_id = p_conversation
      AND e.event_type = 'message' AND e.processing_status = 'recorded'
    ORDER BY e.received_at DESC, e.id DESC LIMIT 1;
  IF v_event IS NULL THEN
    RAISE EXCEPTION 'event missing' USING ERRCODE = 'P0002';
  END IF;
  SELECT m.user_id INTO v_owner FROM app.org_members m
    WHERE m.organization_id = p_org AND m.role = 'gestor' AND m.status = 'active'
    ORDER BY m.created_at, m.user_id LIMIT 1;
  IF v_owner IS NULL THEN
    RAISE EXCEPTION 'no queue owner' USING ERRCODE = '42501';
  END IF;
  UPDATE app.conversations SET mode = 'awaiting_human',
    handoff_reason = p_reason, handoff_requested_at = now(),
    summary_status = 'unavailable'
    WHERE organization_id = p_org AND id = p_conversation;
  UPDATE app.leads SET stage = 'handed_off'
    WHERE organization_id = p_org AND id = v_conversation.lead_id;
  INSERT INTO app.operation_incidents(organization_id, conversation_id,
    cause_event_id, kind, reason, owner_member_id, next_action)
  VALUES (p_org, p_conversation, v_event, 'human_handoff', p_reason,
    v_owner, 'Revisar a pergunta e responder manualmente.')
  RETURNING id INTO v_incident;
  INSERT INTO app.outbox_events(organization_id, event_type, aggregate_id, dedupe_key)
    VALUES (p_org, 'handoff.requested', p_conversation,
      'catalog_handoff:' || v_event::text);
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'handoff.requested');
  RETURN v_incident;
END $$;
ALTER FUNCTION private.handoff_catalog_reply(uuid,uuid,uuid,integer,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.handoff_catalog_reply(uuid,uuid,uuid,integer,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.handoff_catalog_reply(uuid,uuid,uuid,integer,text) TO app_api;
