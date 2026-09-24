CREATE FUNCTION private.current_seller_id(p_org uuid) RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT m.seller_id FROM app.org_members m
  WHERE m.organization_id = p_org AND m.user_id = private.actor_id()
    AND m.role = 'vendedor' AND m.status = 'active' AND m.password_changed
$$;
ALTER FUNCTION private.current_seller_id(uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.current_seller_id(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.current_seller_id(uuid) TO app_api;

CREATE POLICY conversations_assigned_seller_read ON app.conversations FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id())
  AND assigned_seller_id = (SELECT private.current_seller_id(organization_id)));
CREATE POLICY leads_assigned_seller_read ON app.leads FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND EXISTS (
  SELECT 1 FROM app.conversations c WHERE c.organization_id = leads.organization_id
    AND c.lead_id = leads.id
    AND c.assigned_seller_id = (SELECT private.current_seller_id(leads.organization_id))));
CREATE POLICY messages_assigned_seller_read ON app.messages FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND EXISTS (
  SELECT 1 FROM app.conversations c WHERE c.organization_id = messages.organization_id
    AND c.id = messages.conversation_id
    AND c.assigned_seller_id = (SELECT private.current_seller_id(messages.organization_id))));

GRANT UPDATE (next_action) ON app.operation_incidents TO app_bootstrap;

CREATE FUNCTION private.assign_conversation(
  p_org uuid, p_conversation uuid, p_seller uuid, p_reason text, p_version integer
) RETURNS TABLE(mode text, assigned_seller_id uuid, claimed_by uuid, control_version integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_conversation app.conversations%ROWTYPE;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'assignment forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_conversation FROM app.conversations c
    WHERE c.organization_id = p_org AND c.id = p_conversation FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'conversation not found' USING ERRCODE = 'P0002';
  END IF;
  IF v_conversation.control_version <> p_version OR v_conversation.claimed_by IS NOT NULL
     OR v_conversation.mode <> 'awaiting_human' THEN
    RAISE EXCEPTION 'conversation changed' USING ERRCODE = '40001';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM app.sellers s JOIN app.org_members m
    ON m.organization_id = s.organization_id AND m.seller_id = s.id
    WHERE s.organization_id = p_org AND s.id = p_seller AND s.active AND s.available
      AND m.role = 'vendedor' AND m.status = 'active' AND m.password_changed) THEN
    RAISE EXCEPTION 'seller ineligible' USING ERRCODE = '42501';
  END IF;
  UPDATE app.conversations c SET assigned_seller_id = p_seller,
    control_version = c.control_version + 1
    WHERE c.organization_id = p_org AND c.id = p_conversation;
  UPDATE app.operation_incidents i SET next_action = 'Vendedor atribuído; aguardando assunção.'
    WHERE i.organization_id = p_org AND i.conversation_id = p_conversation AND i.state = 'open';
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'conversation.assigned');
  RETURN QUERY SELECT c.mode, c.assigned_seller_id, c.claimed_by, c.control_version
    FROM app.conversations c WHERE c.organization_id = p_org AND c.id = p_conversation;
END $$;
ALTER FUNCTION private.assign_conversation(uuid,uuid,uuid,text,integer) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.assign_conversation(uuid,uuid,uuid,text,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.assign_conversation(uuid,uuid,uuid,text,integer) TO app_api;

CREATE OR REPLACE FUNCTION private.claim_conversation(p_org uuid, p_conversation uuid, p_version integer)
RETURNS TABLE(mode text, claimed_by uuid, control_version integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_actor uuid := private.actor_id();
  v_member app.org_members%ROWTYPE;
  v_conversation app.conversations%ROWTYPE;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR v_actor IS NULL THEN
    RAISE EXCEPTION 'conversation not found' USING ERRCODE = 'P0002';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_conversation FROM app.conversations c
    WHERE c.organization_id = p_org AND c.id = p_conversation FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'conversation not found' USING ERRCODE = 'P0002';
  END IF;
  SELECT * INTO v_member FROM app.org_members m
    WHERE m.organization_id = p_org AND m.user_id = v_actor AND m.status = 'active';
  IF NOT FOUND OR (v_member.role <> 'gestor' AND
      (v_member.role <> 'vendedor' OR NOT v_member.password_changed OR
       v_member.seller_id IS DISTINCT FROM v_conversation.assigned_seller_id OR
       NOT EXISTS (SELECT 1 FROM app.sellers s WHERE s.organization_id = p_org
         AND s.id = v_member.seller_id AND s.active AND s.available))) THEN
    RAISE EXCEPTION 'claim forbidden' USING ERRCODE = '42501';
  END IF;
  IF v_conversation.control_version <> p_version OR v_conversation.claimed_by IS NOT NULL
     OR v_conversation.mode <> 'awaiting_human' THEN
    RAISE EXCEPTION 'conversation changed' USING ERRCODE = '40001';
  END IF;
  UPDATE app.conversations c SET mode = 'human', claimed_by = v_actor,
    control_version = c.control_version + 1
    WHERE c.organization_id = p_org AND c.id = p_conversation;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, v_actor, 'conversation.claimed');
  RETURN QUERY SELECT c.mode, c.claimed_by, c.control_version
    FROM app.conversations c WHERE c.organization_id = p_org AND c.id = p_conversation;
END $$;
