ALTER TABLE app.conversations
  ADD COLUMN control_version integer NOT NULL DEFAULT 1 CHECK (control_version > 0);

CREATE FUNCTION private.claim_conversation(p_org uuid, p_conversation uuid, p_version integer)
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
  IF NOT FOUND OR v_member.role <> 'gestor' THEN
    RAISE EXCEPTION 'claim forbidden' USING ERRCODE = '42501';
  END IF;
  IF v_conversation.control_version <> p_version OR v_conversation.claimed_by IS NOT NULL
     OR v_conversation.mode NOT IN ('awaiting_human', 'human') THEN
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
ALTER FUNCTION private.claim_conversation(uuid,uuid,integer) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.claim_conversation(uuid,uuid,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.claim_conversation(uuid,uuid,integer) TO app_api;
