GRANT USAGE ON SCHEMA private TO app_worker;

CREATE FUNCTION private.worker_due_organizations()
RETURNS TABLE(organization_id uuid)
LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
  SELECT DISTINCT i.organization_id FROM app.outbound_intents i
  JOIN app.delivery_attempts a ON a.organization_id = i.organization_id
    AND a.intent_id = i.id
  WHERE i.status = 'dispatching' AND a.state = 'dispatching'
    AND a.started_at <= now() - interval '120 seconds'
  ORDER BY i.organization_id LIMIT 100
$$;
ALTER FUNCTION private.worker_due_organizations() OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.worker_due_organizations() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.worker_due_organizations() TO app_worker;

CREATE FUNCTION private.worker_recover_organization(p_org uuid)
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_candidate record; v_intent app.outbound_intents%ROWTYPE;
  v_started timestamptz; v_count integer := 0;
BEGIN
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  IF NOT FOUND THEN
    RETURN 0;
  END IF;
  FOR v_candidate IN
    SELECT i.id, i.conversation_id FROM app.outbound_intents i
    JOIN app.delivery_attempts a ON a.organization_id = i.organization_id
      AND a.intent_id = i.id
    WHERE i.organization_id = p_org AND i.status = 'dispatching'
      AND a.state = 'dispatching'
      AND a.started_at <= now() - interval '120 seconds'
    ORDER BY i.conversation_id, i.id LIMIT 100
  LOOP
    PERFORM 1 FROM app.conversations c WHERE c.organization_id = p_org
      AND c.id = v_candidate.conversation_id FOR UPDATE;
    SELECT * INTO v_intent FROM app.outbound_intents i WHERE i.organization_id = p_org
      AND i.id = v_candidate.id FOR UPDATE;
    SELECT a.started_at INTO v_started FROM app.delivery_attempts a
      WHERE a.organization_id = p_org AND a.intent_id = v_candidate.id
        AND a.state = 'dispatching';
    IF v_intent.status <> 'dispatching' OR v_started IS NULL OR
       v_started > now() - interval '120 seconds' THEN
      CONTINUE;
    END IF;
    UPDATE app.outbound_intents i SET status = 'unknown', updated_at = now(),
      error_code = 'LEASE_EXPIRED' WHERE i.organization_id = p_org AND i.id = v_candidate.id;
    UPDATE app.delivery_attempts a SET state = 'unknown', finished_at = now(),
      error_code = 'LEASE_EXPIRED' WHERE a.organization_id = p_org
        AND a.intent_id = v_candidate.id AND a.state = 'dispatching';
    INSERT INTO app.delivery_incidents(organization_id, intent_id, reason, next_action)
      VALUES (p_org, v_candidate.id, 'confirmation_lost',
        'Tentativa sem confirmação após lease vencida. Verificar o canal; Não reenviar esta intenção.')
      ON CONFLICT (organization_id, intent_id) DO NOTHING;
    v_count := v_count + 1;
  END LOOP;
  RETURN v_count;
END $$;
ALTER FUNCTION private.worker_recover_organization(uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.worker_recover_organization(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.worker_recover_organization(uuid) TO app_worker;
