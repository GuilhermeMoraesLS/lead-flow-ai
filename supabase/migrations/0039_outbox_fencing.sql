ALTER TABLE app.outbox_events ADD COLUMN recovery_token uuid,
  ADD COLUMN recovery_claimed_until timestamptz;
CREATE INDEX outbox_recovery_claim ON app.outbox_events(available_at, recovery_claimed_until, id)
  WHERE published_at IS NULL;

CREATE FUNCTION private.worker_claim_outbox()
RETURNS TABLE(organization_id uuid, outbox_id uuid, claim_token uuid)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  RETURN QUERY
  WITH due AS (
    SELECT o.id FROM app.outbox_events o
    WHERE o.published_at IS NULL AND o.available_at <= now()
      AND (o.recovery_claimed_until IS NULL OR o.recovery_claimed_until <= now())
    ORDER BY o.available_at, o.id LIMIT 100 FOR UPDATE SKIP LOCKED
  )
  UPDATE app.outbox_events o SET recovery_token = gen_random_uuid(),
    recovery_claimed_until = now() + interval '120 seconds'
  FROM due WHERE o.id = due.id
  RETURNING o.organization_id, o.id, o.recovery_token;
END $$;
ALTER FUNCTION private.worker_claim_outbox() OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.worker_claim_outbox() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.worker_claim_outbox() TO app_worker;

CREATE OR REPLACE FUNCTION private.worker_consume_outbox(p_org uuid, p_outbox uuid, p_token uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_event app.outbox_events%ROWTYPE; v_added integer;
BEGIN
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  IF NOT FOUND THEN RETURN false; END IF;
  SELECT * INTO v_event FROM app.outbox_events o
    WHERE o.organization_id = p_org AND o.id = p_outbox FOR UPDATE;
  IF NOT FOUND OR v_event.published_at IS NOT NULL OR
     v_event.recovery_token IS DISTINCT FROM p_token OR
     v_event.recovery_claimed_until <= now() THEN
    RETURN false;
  END IF;
  INSERT INTO app.outbox_effects(organization_id, outbox_id) VALUES (p_org, p_outbox)
    ON CONFLICT DO NOTHING;
  GET DIAGNOSTICS v_added = ROW_COUNT;
  UPDATE app.outbox_events o SET published_at = now(), recovery_token = NULL,
    recovery_claimed_until = NULL WHERE o.organization_id = p_org AND o.id = p_outbox;
  RETURN v_added = 1;
END $$;
ALTER FUNCTION private.worker_consume_outbox(uuid,uuid,uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.worker_consume_outbox(uuid,uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.worker_consume_outbox(uuid,uuid,uuid) TO app_worker;
REVOKE ALL ON FUNCTION private.worker_consume_outbox(uuid,uuid) FROM app_worker;
