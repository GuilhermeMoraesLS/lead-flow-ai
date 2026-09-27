-- The sender serializes on the organization before an external attempt.
CREATE POLICY catalog_runs_bootstrap ON app.catalog_agent_runs TO app_bootstrap
  USING (true) WITH CHECK (true);
GRANT SELECT, UPDATE ON app.catalog_agent_runs TO app_bootstrap;

CREATE OR REPLACE FUNCTION private.authorize_test_dispatch(p_org uuid, p_intent uuid)
RETURNS TABLE(started boolean, current_status text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_kind text; v_revision bigint; v_run app.catalog_agent_runs%ROWTYPE;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT EXISTS (
    SELECT 1 FROM app.org_members m WHERE m.organization_id = p_org
      AND m.user_id = private.actor_id() AND m.status = 'active'
  ) THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  SELECT o.commercial_revision INTO v_revision FROM app.organizations o
    WHERE o.id = p_org FOR UPDATE;
  SELECT i.kind INTO v_kind FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'intent not found' USING ERRCODE = 'P0002';
  END IF;
  IF v_kind = 'synthetic_auto' AND NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  SELECT * INTO v_run FROM app.catalog_agent_runs r
    WHERE r.organization_id = p_org AND r.intent_id = p_intent;
  IF FOUND AND v_run.commercial_revision <> v_revision THEN
    UPDATE app.outbound_intents i SET status = 'cancelled',
      cancellation_reason = 'commercial_revision_changed', updated_at = now()
      WHERE i.organization_id = p_org AND i.id = p_intent AND i.status = 'pending';
    UPDATE app.catalog_agent_runs r SET status = 'handoff',
      failure_code = 'commercial_revision_changed', updated_at = now()
      WHERE r.organization_id = p_org AND r.id = v_run.id;
    RETURN QUERY SELECT false, 'cancelled'::text;
    RETURN;
  END IF;
  RETURN QUERY SELECT s.started, s.current_status
    FROM private.start_test_dispatch(p_org, p_intent) s;
END $$;
ALTER FUNCTION private.authorize_test_dispatch(uuid,uuid) OWNER TO app_bootstrap;
