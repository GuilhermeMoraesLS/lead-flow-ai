ALTER TABLE app.outbox_events ADD COLUMN recovery_attempts integer NOT NULL DEFAULT 0,
  ADD COLUMN recovery_state text NOT NULL DEFAULT 'ready'
    CHECK (recovery_state IN ('ready', 'exhausted')),
  ADD COLUMN recovery_deadline timestamptz;

CREATE TABLE app.outbox_recovery_incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  outbox_id uuid NOT NULL,
  reason text NOT NULL,
  owner_member_id uuid NOT NULL,
  next_action text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, outbox_id),
  FOREIGN KEY (organization_id, outbox_id)
    REFERENCES app.outbox_events(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, owner_member_id)
    REFERENCES app.org_members(organization_id, user_id) ON DELETE RESTRICT
);
ALTER TABLE app.outbox_recovery_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.outbox_recovery_incidents FORCE ROW LEVEL SECURITY;
CREATE POLICY outbox_incident_manager_read ON app.outbox_recovery_incidents FOR SELECT TO app_api
  USING (organization_id = (SELECT private.org_id()) AND
    (SELECT private.gestor_of(organization_id)));
CREATE POLICY outbox_incident_bootstrap ON app.outbox_recovery_incidents TO app_bootstrap
  USING (true) WITH CHECK (true);
GRANT SELECT ON app.outbox_recovery_incidents TO app_api;
GRANT SELECT, INSERT ON app.outbox_recovery_incidents TO app_bootstrap;

CREATE OR REPLACE FUNCTION private.worker_claim_outbox()
RETURNS TABLE(organization_id uuid, outbox_id uuid, claim_token uuid)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  RETURN QUERY
  WITH due AS (
    SELECT o.id FROM app.outbox_events o
    WHERE o.published_at IS NULL AND o.recovery_state = 'ready'
      AND o.available_at <= now()
      AND (o.recovery_claimed_until IS NULL OR o.recovery_claimed_until <= now())
    ORDER BY o.available_at, o.id LIMIT 100 FOR UPDATE SKIP LOCKED
  )
  UPDATE app.outbox_events o SET recovery_token = gen_random_uuid(),
    recovery_claimed_until = now() + interval '120 seconds'
  FROM due WHERE o.id = due.id
  RETURNING o.organization_id, o.id, o.recovery_token;
END $$;

CREATE FUNCTION private.worker_retry_outbox(
  p_org uuid, p_outbox uuid, p_token uuid, p_reason text,
  p_retry_after_seconds integer DEFAULT 0
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_event app.outbox_events%ROWTYPE; v_attempts integer;
  v_delay integer; v_deadline timestamptz; v_owner uuid;
BEGIN
  IF p_reason NOT IN ('serialization_failure', 'deadlock_detected', 'rate_limited') OR
     p_retry_after_seconds < 0 OR p_retry_after_seconds > 300 THEN
    RAISE EXCEPTION 'unsafe retry' USING ERRCODE = '22023';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_event FROM app.outbox_events o
    WHERE o.organization_id = p_org AND o.id = p_outbox FOR UPDATE;
  IF NOT FOUND OR v_event.published_at IS NOT NULL OR
     v_event.recovery_state <> 'ready' OR
     v_event.recovery_token IS DISTINCT FROM p_token OR
     v_event.recovery_claimed_until <= now() THEN
    RETURN 'stale';
  END IF;
  v_attempts := v_event.recovery_attempts + 1;
  v_deadline := coalesce(v_event.recovery_deadline, now() + interval '5 minutes');
  v_delay := greatest(p_retry_after_seconds,
    least(60, (2 * power(2, v_attempts - 1) * (0.5 + random()))::integer));
  IF v_attempts >= 5 OR now() + make_interval(secs => v_delay) >= v_deadline THEN
    SELECT m.user_id INTO v_owner FROM app.org_members m
      WHERE m.organization_id = p_org AND m.role = 'gestor' AND m.status = 'active'
      ORDER BY m.created_at, m.user_id LIMIT 1;
    IF v_owner IS NULL THEN
      RAISE EXCEPTION 'no incident owner' USING ERRCODE = '42501';
    END IF;
    UPDATE app.outbox_events o SET recovery_attempts = v_attempts,
      recovery_state = 'exhausted', recovery_deadline = v_deadline,
      recovery_token = NULL, recovery_claimed_until = NULL
      WHERE o.organization_id = p_org AND o.id = p_outbox;
    INSERT INTO app.outbox_recovery_incidents
      (organization_id, outbox_id, reason, owner_member_id, next_action)
      VALUES (p_org, p_outbox, p_reason, v_owner,
        'Verificar a falha e o estado do evento antes de qualquer nova tentativa.')
      ON CONFLICT (organization_id, outbox_id) DO NOTHING;
    RETURN 'exhausted';
  END IF;
  UPDATE app.outbox_events o SET recovery_attempts = v_attempts,
    recovery_deadline = v_deadline, recovery_token = NULL,
    recovery_claimed_until = now() + make_interval(secs => v_delay)
    WHERE o.organization_id = p_org AND o.id = p_outbox;
  RETURN 'scheduled';
END $$;
ALTER FUNCTION private.worker_retry_outbox(uuid,uuid,uuid,text,integer) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.worker_retry_outbox(uuid,uuid,uuid,text,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.worker_retry_outbox(uuid,uuid,uuid,text,integer) TO app_worker;
