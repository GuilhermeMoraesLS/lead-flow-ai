CREATE FUNCTION private.forward_opted_out_test_event(
  p_channel uuid, p_token_hash text, p_external_event text
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_org uuid; v_event app.inbound_events%ROWTYPE;
  v_conversation app.conversations%ROWTYPE; v_owner uuid;
BEGIN
  SELECT c.organization_id INTO v_org FROM app.channels c
    WHERE c.id = p_channel AND c.token_hash = p_token_hash;
  IF v_org IS NULL THEN
    RAISE EXCEPTION 'invalid channel token' USING ERRCODE = '28000';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = v_org FOR UPDATE;
  SELECT * INTO v_event FROM app.inbound_events e WHERE e.organization_id = v_org
    AND e.channel_id = p_channel AND e.external_event_id = p_external_event
    AND e.event_type = 'message' AND e.processing_status = 'recorded';
  IF NOT FOUND OR v_event.conversation_id IS NULL THEN
    RAISE EXCEPTION 'recorded message required' USING ERRCODE = 'P0002';
  END IF;
  SELECT * INTO v_conversation FROM app.conversations c WHERE c.organization_id = v_org
    AND c.id = v_event.conversation_id FOR UPDATE;
  IF v_conversation.mode <> 'automatic' OR NOT EXISTS (
    SELECT 1 FROM app.contact_opt_outs o WHERE o.organization_id = v_org
      AND o.channel_id = p_channel AND o.lead_id = v_conversation.lead_id) THEN
    RETURN false;
  END IF;
  SELECT m.user_id INTO v_owner FROM app.org_members m WHERE m.organization_id = v_org
    AND m.role = 'gestor' AND m.status = 'active' ORDER BY m.created_at, m.user_id LIMIT 1;
  IF v_owner IS NULL THEN
    RAISE EXCEPTION 'no queue owner' USING ERRCODE = '42501';
  END IF;
  UPDATE app.conversations c SET mode = 'awaiting_human',
    handoff_reason = 'opt_out', handoff_requested_at = now(), summary_status = 'unavailable',
    control_version = c.control_version + 1
    WHERE c.organization_id = v_org AND c.id = v_conversation.id;
  UPDATE app.outbound_intents i SET status = 'cancelled',
    cancellation_reason = 'opt_out', updated_at = now()
    WHERE i.organization_id = v_org AND i.conversation_id = v_conversation.id
      AND i.kind = 'synthetic_auto' AND i.status = 'pending';
  INSERT INTO app.operation_incidents(organization_id, conversation_id, cause_event_id,
    kind, reason, owner_member_id, next_action)
    VALUES (v_org, v_conversation.id, v_event.id, 'human_handoff', 'opt_out',
      v_owner, 'Atender manualmente; opt-out permanece ativo neste canal.');
  INSERT INTO app.outbox_events(organization_id, event_type, aggregate_id, dedupe_key)
    VALUES (v_org, 'handoff.requested', v_conversation.id, 'handoff:' || v_event.id::text);
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (v_org, v_owner, 'contact.opt_out_returned');
  RETURN true;
END $$;
ALTER FUNCTION private.forward_opted_out_test_event(uuid,text,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.forward_opted_out_test_event(uuid,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.forward_opted_out_test_event(uuid,text,text) TO app_api;
