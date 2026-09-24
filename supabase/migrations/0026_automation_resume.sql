ALTER TABLE app.conversations ADD COLUMN contact_blocked boolean NOT NULL DEFAULT false;
GRANT UPDATE ON app.conversations, app.operation_incidents TO app_bootstrap;

CREATE OR REPLACE FUNCTION private.enable_test_automation(p_org uuid)
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_epoch integer;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'control forbidden' USING ERRCODE = '42501';
  END IF;
  UPDATE app.organizations o SET simulation_enabled = true,
    automation_epoch = automation_epoch + 1
    WHERE o.id = p_org RETURNING automation_epoch INTO v_epoch;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'test_automation.enabled');
  RETURN v_epoch;
END $$;
ALTER FUNCTION private.enable_test_automation(uuid) OWNER TO app_bootstrap;

CREATE FUNCTION private.set_test_contact_block(
  p_org uuid, p_conversation uuid, p_blocked boolean
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_version integer;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'control forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  UPDATE app.conversations c SET contact_blocked = p_blocked,
    control_version = c.control_version + 1
    WHERE c.organization_id = p_org AND c.id = p_conversation
    RETURNING c.control_version INTO v_version;
  IF v_version IS NULL THEN
    RAISE EXCEPTION 'conversation not found' USING ERRCODE = 'P0002';
  END IF;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'test_contact_block.changed');
  RETURN v_version;
END $$;
ALTER FUNCTION private.set_test_contact_block(uuid,uuid,boolean) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.set_test_contact_block(uuid,uuid,boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.set_test_contact_block(uuid,uuid,boolean) TO app_api;

CREATE FUNCTION private.resume_automation(p_org uuid)
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_epoch integer;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'control forbidden' USING ERRCODE = '42501';
  END IF;
  UPDATE app.organizations o SET automation_paused = false,
    automation_epoch = automation_epoch + 1
    WHERE o.id = p_org RETURNING o.automation_epoch INTO v_epoch;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'automation.resumed');
  RETURN v_epoch;
END $$;
ALTER FUNCTION private.resume_automation(uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.resume_automation(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.resume_automation(uuid) TO app_api;

CREATE FUNCTION private.resume_ai(
  p_org uuid, p_conversation uuid, p_version integer
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_org app.organizations%ROWTYPE; v_conversation app.conversations%ROWTYPE;
  v_member app.org_members%ROWTYPE; v_stage text; v_version integer;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR private.actor_id() IS NULL THEN
    RAISE EXCEPTION 'conversation not found' USING ERRCODE = 'P0002';
  END IF;
  SELECT * INTO v_org FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_conversation FROM app.conversations c
    WHERE c.organization_id = p_org AND c.id = p_conversation FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'conversation not found' USING ERRCODE = 'P0002';
  END IF;
  SELECT * INTO v_member FROM app.org_members m WHERE m.organization_id = p_org
    AND m.user_id = private.actor_id() AND m.status = 'active';
  IF NOT FOUND OR (v_member.role <> 'gestor' AND
      (v_member.role <> 'vendedor' OR NOT v_member.password_changed OR
       v_conversation.claimed_by IS DISTINCT FROM v_member.user_id OR
       v_member.seller_id IS DISTINCT FROM v_conversation.assigned_seller_id OR
       NOT EXISTS (SELECT 1 FROM app.sellers s WHERE s.organization_id = p_org
         AND s.id = v_member.seller_id AND s.active AND s.available))) THEN
    RAISE EXCEPTION 'resume forbidden' USING ERRCODE = '42501';
  END IF;
  SELECT l.stage INTO v_stage FROM app.leads l WHERE l.organization_id = p_org
    AND l.id = v_conversation.lead_id;
  IF v_conversation.control_version <> p_version THEN
    RAISE EXCEPTION 'conversation changed' USING ERRCODE = '40001';
  END IF;
  IF v_conversation.mode <> 'human' OR NOT v_org.simulation_enabled OR
     v_org.automation_paused OR v_conversation.contact_blocked OR
     v_stage IN ('won', 'lost') OR
     EXISTS (SELECT 1 FROM app.delivery_incidents d JOIN app.outbound_intents i
       ON i.organization_id = d.organization_id AND i.id = d.intent_id
       WHERE d.organization_id = p_org AND i.conversation_id = p_conversation
         AND d.state = 'open') OR
     EXISTS (SELECT 1 FROM app.outbound_intents i WHERE i.organization_id = p_org
       AND i.conversation_id = p_conversation AND i.status = 'dispatching') THEN
    RAISE EXCEPTION 'automatic reply ineligible' USING ERRCODE = '23514';
  END IF;
  UPDATE app.conversations c SET mode = 'automatic', claimed_by = NULL,
    control_version = c.control_version + 1
    WHERE c.organization_id = p_org AND c.id = p_conversation
    RETURNING c.control_version INTO v_version;
  UPDATE app.operation_incidents i SET state = 'resolved'
    WHERE i.organization_id = p_org AND i.conversation_id = p_conversation
      AND i.state = 'open';
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'conversation.resumed_ai');
  RETURN v_version;
END $$;
ALTER FUNCTION private.resume_ai(uuid,uuid,integer) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.resume_ai(uuid,uuid,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.resume_ai(uuid,uuid,integer) TO app_api;
