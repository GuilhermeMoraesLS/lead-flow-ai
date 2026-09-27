CREATE OR REPLACE FUNCTION private.authorize_test_dispatch(p_org uuid, p_intent uuid)
RETURNS TABLE(started boolean, current_status text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_kind text; v_status text; v_revision bigint;
  v_run app.catalog_agent_runs%ROWTYPE;
  v_conversation app.conversations%ROWTYPE;
  v_latest uuid;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT EXISTS (
    SELECT 1 FROM app.org_members m WHERE m.organization_id = p_org
      AND m.user_id = private.actor_id() AND m.status = 'active'
  ) THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  SELECT o.commercial_revision INTO v_revision FROM app.organizations o
    WHERE o.id = p_org FOR UPDATE;
  SELECT i.kind, i.status INTO v_kind, v_status FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'intent not found' USING ERRCODE = 'P0002';
  END IF;
  IF v_kind = 'synthetic_auto' AND NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  IF v_status = 'pending' THEN
    SELECT * INTO v_run FROM app.catalog_agent_runs r
      WHERE r.organization_id = p_org AND r.intent_id = p_intent;
    IF FOUND AND v_run.commercial_revision <> v_revision THEN
      UPDATE app.outbound_intents i SET status = 'cancelled',
        cancellation_reason = 'commercial_revision_changed', updated_at = now()
        WHERE i.organization_id = p_org AND i.id = p_intent;
      UPDATE app.catalog_agent_runs r SET status = 'handoff',
        failure_code = 'commercial_revision_changed', updated_at = now()
        WHERE r.organization_id = p_org AND r.id = v_run.id;
      SELECT * INTO v_conversation FROM app.conversations c
        WHERE c.organization_id = p_org AND c.id = v_run.conversation_id;
      SELECT m.id INTO v_latest FROM app.messages m
        WHERE m.organization_id = p_org
          AND m.conversation_id = v_run.conversation_id
        ORDER BY m.received_at DESC, m.id DESC LIMIT 1;
      IF v_conversation.mode = 'automatic'
         AND v_conversation.claimed_by IS NULL
         AND NOT v_conversation.contact_blocked
         AND v_latest = v_run.message_id THEN
        PERFORM private.handoff_catalog_reply(p_org, v_run.conversation_id,
          v_run.message_id, v_conversation.input_revision, 'catalog_conflict');
      END IF;
      RETURN QUERY SELECT false, 'cancelled'::text;
      RETURN;
    END IF;
  END IF;
  RETURN QUERY SELECT s.started, s.current_status
    FROM private.start_test_dispatch(p_org, p_intent) s;
END $$;
ALTER FUNCTION private.authorize_test_dispatch(uuid,uuid) OWNER TO app_bootstrap;
