CREATE OR REPLACE FUNCTION private.start_test_dispatch(p_org uuid, p_intent uuid)
RETURNS TABLE(started boolean, current_status text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_intent app.outbound_intents%ROWTYPE; v_conversation app.conversations%ROWTYPE;
  v_org app.organizations%ROWTYPE;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  SELECT * INTO v_org FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_intent FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'intent not found' USING ERRCODE = 'P0002';
  END IF;
  IF NOT private.gestor_of(p_org) AND private.actor_id() IS DISTINCT FROM v_intent.author_id THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  SELECT * INTO v_conversation FROM app.conversations c
    WHERE c.organization_id = p_org AND c.id = v_intent.conversation_id FOR UPDATE;
  SELECT * INTO v_intent FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent FOR UPDATE;
  IF v_intent.status <> 'pending' THEN
    RETURN QUERY SELECT false, v_intent.status;
    RETURN;
  END IF;
  IF v_intent.kind = 'synthetic_auto' THEN
    IF NOT v_org.simulation_enabled OR v_org.automation_paused OR
       v_conversation.mode <> 'automatic' OR v_conversation.claimed_by IS NOT NULL OR
       EXISTS (SELECT 1 FROM app.delivery_incidents d JOIN app.outbound_intents i
         ON i.organization_id = d.organization_id AND i.id = d.intent_id
         WHERE d.organization_id = p_org AND i.conversation_id = v_conversation.id
           AND d.state = 'open') THEN
      UPDATE app.outbound_intents i SET status = 'cancelled', updated_at = now(),
        cancellation_reason = 'control_changed'
        WHERE i.organization_id = p_org AND i.id = p_intent;
      RETURN QUERY SELECT false, 'cancelled'::text;
      RETURN;
    END IF;
  ELSIF v_conversation.mode <> 'human' OR
     v_conversation.claimed_by IS DISTINCT FROM v_intent.author_id OR
     NOT EXISTS (SELECT 1 FROM app.org_members m WHERE m.organization_id = p_org
       AND m.user_id = v_intent.author_id AND m.status = 'active'
       AND (m.role = 'gestor' OR (m.role = 'vendedor' AND m.password_changed
         AND m.seller_id = v_conversation.assigned_seller_id AND EXISTS (
           SELECT 1 FROM app.sellers s WHERE s.organization_id = p_org
             AND s.id = m.seller_id AND s.active AND s.available)))) THEN
    RAISE EXCEPTION 'sender no longer authorized' USING ERRCODE = '42501';
  END IF;
  IF EXISTS (SELECT 1 FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.conversation_id = v_intent.conversation_id
      AND i.status = 'dispatching') THEN
    RETURN QUERY SELECT false, 'pending'::text;
    RETURN;
  END IF;
  UPDATE app.outbound_intents i SET status = 'dispatching', updated_at = now()
    WHERE i.organization_id = p_org AND i.id = p_intent;
  INSERT INTO app.delivery_attempts(organization_id, intent_id, state)
    VALUES (p_org, p_intent, 'dispatching');
  RETURN QUERY SELECT true, 'dispatching'::text;
END $$;
ALTER FUNCTION private.start_test_dispatch(uuid,uuid) OWNER TO app_bootstrap;
