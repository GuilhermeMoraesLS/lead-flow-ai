-- Test-only automation remains separate from the incomplete real activation path.
ALTER TABLE app.organizations
  ADD COLUMN simulation_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN automation_paused boolean NOT NULL DEFAULT false,
  ADD COLUMN automation_epoch integer NOT NULL DEFAULT 1 CHECK (automation_epoch > 0);
ALTER TABLE app.outbound_intents
  ADD COLUMN kind text NOT NULL DEFAULT 'human_reply'
    CHECK (kind IN ('human_reply', 'synthetic_auto')),
  ADD COLUMN cancellation_reason text;
ALTER TABLE app.outbound_intents DROP CONSTRAINT outbound_intents_status_check;
ALTER TABLE app.outbound_intents ADD CONSTRAINT outbound_intents_status_check
  CHECK (status IN ('pending', 'dispatching', 'accepted', 'rejected', 'unknown', 'cancelled'));
ALTER TABLE app.outbox_events DROP CONSTRAINT outbox_events_event_type_check;
ALTER TABLE app.outbox_events ADD CONSTRAINT outbox_events_event_type_check
  CHECK (event_type IN ('inbound.recorded', 'handoff.requested',
                       'human_reply.requested', 'synthetic_auto.requested'));
GRANT UPDATE ON app.organizations TO app_bootstrap;

CREATE FUNCTION private.enable_test_automation(p_org uuid)
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_epoch integer;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'control forbidden' USING ERRCODE = '42501';
  END IF;
  UPDATE app.organizations o SET simulation_enabled = true,
    automation_paused = false, automation_epoch = automation_epoch + 1
    WHERE o.id = p_org RETURNING automation_epoch INTO v_epoch;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'test_automation.enabled');
  RETURN v_epoch;
END $$;
ALTER FUNCTION private.enable_test_automation(uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.enable_test_automation(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.enable_test_automation(uuid) TO app_api;

CREATE FUNCTION private.prepare_test_auto_intent(
  p_org uuid, p_conversation uuid, p_command uuid, p_text text
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_org app.organizations%ROWTYPE; v_conversation app.conversations%ROWTYPE;
  v_intent uuid; v_actor uuid := private.actor_id();
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'preparation forbidden' USING ERRCODE = '42501';
  END IF;
  SELECT * INTO v_org FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_conversation FROM app.conversations c
    WHERE c.organization_id = p_org AND c.id = p_conversation FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'conversation not found' USING ERRCODE = 'P0002';
  END IF;
  IF NOT v_org.simulation_enabled OR v_org.automation_paused OR
     v_conversation.mode <> 'automatic' OR v_conversation.claimed_by IS NOT NULL OR
     EXISTS (SELECT 1 FROM app.delivery_incidents d JOIN app.outbound_intents i
       ON i.organization_id = d.organization_id AND i.id = d.intent_id
       WHERE d.organization_id = p_org AND i.conversation_id = p_conversation
         AND d.state = 'open') THEN
    RAISE EXCEPTION 'automatic reply ineligible' USING ERRCODE = '42501';
  END IF;
  INSERT INTO app.outbound_intents(
    organization_id, conversation_id, channel_id, command_id, author_id, text, kind
  ) VALUES (p_org, p_conversation, v_conversation.channel_id, p_command,
            v_actor, p_text, 'synthetic_auto') RETURNING id INTO v_intent;
  INSERT INTO app.outbox_events(organization_id, event_type, aggregate_id, dedupe_key)
    VALUES (p_org, 'synthetic_auto.requested', p_conversation,
            'synthetic_auto:' || v_intent::text);
  RETURN v_intent;
END $$;
ALTER FUNCTION private.prepare_test_auto_intent(uuid,uuid,uuid,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.prepare_test_auto_intent(uuid,uuid,uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.prepare_test_auto_intent(uuid,uuid,uuid,text) TO app_api;

CREATE FUNCTION private.pause_automation(p_org uuid)
RETURNS TABLE(epoch integer, pending_attempts integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_conversation uuid; v_epoch integer; v_pending integer := 0;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'control forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  UPDATE app.organizations o SET automation_paused = true,
    automation_epoch = automation_epoch + 1
    WHERE o.id = p_org RETURNING o.automation_epoch INTO v_epoch;
  FOR v_conversation IN SELECT DISTINCT i.conversation_id FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.kind = 'synthetic_auto'
      AND i.status IN ('pending', 'dispatching') ORDER BY i.conversation_id
  LOOP
    PERFORM 1 FROM app.conversations c
      WHERE c.organization_id = p_org AND c.id = v_conversation FOR UPDATE;
    UPDATE app.outbound_intents i SET status = 'cancelled',
      cancellation_reason = 'global_pause', updated_at = now()
      WHERE i.organization_id = p_org AND i.conversation_id = v_conversation
        AND i.kind = 'synthetic_auto' AND i.status = 'pending';
    SELECT v_pending + count(*) INTO v_pending FROM app.outbound_intents i
      WHERE i.organization_id = p_org AND i.conversation_id = v_conversation
        AND i.kind = 'synthetic_auto' AND i.status = 'dispatching';
  END LOOP;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'automation.paused');
  RETURN QUERY SELECT v_epoch, v_pending;
END $$;
ALTER FUNCTION private.pause_automation(uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.pause_automation(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.pause_automation(uuid) TO app_api;
