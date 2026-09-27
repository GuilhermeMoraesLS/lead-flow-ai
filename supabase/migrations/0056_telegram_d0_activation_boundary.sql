-- Activation never releases old, sealed demonstration messages to the sender.
ALTER TABLE app.organizations ADD COLUMN d0_activated_at timestamptz;
GRANT UPDATE ON app.telegram_message_batches TO app_bootstrap;
CREATE POLICY telegram_batches_bootstrap_update ON app.telegram_message_batches
  FOR UPDATE TO app_bootstrap USING (true) WITH CHECK (true);

CREATE OR REPLACE FUNCTION private.enable_telegram_d0(p_org uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_activated_at timestamptz;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'activation forbidden' USING ERRCODE = '42501';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM app.telegram_provisioning t
      WHERE t.organization_id = p_org AND t.status = 'connected')
    OR NOT EXISTS (SELECT 1 FROM app.products p
      WHERE p.organization_id = p_org AND p.status = 'ready' AND p.available)
    OR NOT EXISTS (SELECT 1 FROM app.agents a
      WHERE a.organization_id = p_org AND length(trim(a.instructions)) > 0) THEN
    RAISE EXCEPTION 'D0 prerequisites missing' USING ERRCODE = '23514';
  END IF;
  UPDATE app.organizations o SET d0_enabled = true, simulation_enabled = true,
    d0_activated_at = COALESCE(o.d0_activated_at, now())
    WHERE o.id = p_org AND NOT o.automation_paused
    RETURNING d0_activated_at INTO v_activated_at;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'automation paused' USING ERRCODE = '23514';
  END IF;
  UPDATE app.telegram_message_batches b SET status = 'processed',
    error_code = 'before_activation'
    WHERE b.organization_id = p_org AND b.status = 'ready'
      AND b.created_at < v_activated_at;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'telegram_d0.enabled');
  RETURN true;
END $$;
ALTER FUNCTION private.enable_telegram_d0(uuid) OWNER TO app_bootstrap;

CREATE OR REPLACE FUNCTION private.worker_telegram_due()
RETURNS TABLE(batch_id uuid) LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
  SELECT b.id FROM app.telegram_message_batches b
  JOIN app.organizations o ON o.id = b.organization_id
  WHERE b.status = 'ready' AND o.d0_enabled
    AND b.created_at >= o.d0_activated_at
  ORDER BY b.created_at, b.id LIMIT 100
$$;
ALTER FUNCTION private.worker_telegram_due() OWNER TO app_bootstrap;
