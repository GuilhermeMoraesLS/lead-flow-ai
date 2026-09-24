CREATE OR REPLACE FUNCTION private.authorize_test_dispatch(p_org uuid, p_intent uuid)
RETURNS TABLE(started boolean, current_status text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_kind text;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT EXISTS (
    SELECT 1 FROM app.org_members m WHERE m.organization_id = p_org
      AND m.user_id = private.actor_id() AND m.status = 'active'
  ) THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT i.kind INTO v_kind FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'intent not found' USING ERRCODE = 'P0002';
  END IF;
  IF v_kind = 'synthetic_auto' AND NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  RETURN QUERY SELECT s.started, s.current_status
    FROM private.start_test_dispatch(p_org, p_intent) s;
END $$;
ALTER FUNCTION private.authorize_test_dispatch(uuid,uuid) OWNER TO app_bootstrap;
