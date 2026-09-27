-- D0 is an explicit, local demonstration state, separate from M1 readiness.
ALTER TABLE app.organizations ADD COLUMN d0_enabled boolean NOT NULL DEFAULT false;
ALTER TABLE app.telegram_message_batches
  ADD COLUMN claimed_at timestamptz,
  ADD COLUMN conversation_id uuid,
  ADD COLUMN run_id uuid,
  ADD COLUMN intent_id uuid,
  ADD COLUMN error_code text,
  ADD CONSTRAINT telegram_batch_conversation FOREIGN KEY (organization_id, conversation_id)
    REFERENCES app.conversations(organization_id, id) ON DELETE RESTRICT,
  ADD CONSTRAINT telegram_batch_run FOREIGN KEY (organization_id, run_id)
    REFERENCES app.catalog_agent_runs(organization_id, id) ON DELETE RESTRICT,
  ADD CONSTRAINT telegram_batch_intent FOREIGN KEY (organization_id, intent_id)
    REFERENCES app.outbound_intents(organization_id, id) ON DELETE RESTRICT;
CREATE INDEX telegram_batches_ready ON app.telegram_message_batches(created_at, id)
  WHERE status = 'ready';
GRANT UPDATE (status, claimed_at, conversation_id, run_id, intent_id, error_code)
  ON app.telegram_message_batches TO app_worker;

CREATE FUNCTION private.worker_telegram_manager(p_org uuid)
RETURNS uuid LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
  SELECT m.user_id FROM app.org_members m WHERE m.organization_id = p_org
    AND m.role = 'gestor' AND m.status = 'active'
  ORDER BY m.created_at, m.user_id LIMIT 1
$$;
ALTER FUNCTION private.worker_telegram_manager(uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.worker_telegram_manager(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.worker_telegram_manager(uuid) TO app_worker;

CREATE FUNCTION private.enable_telegram_d0(p_org uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
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
  UPDATE app.organizations o SET d0_enabled = true, simulation_enabled = true
    WHERE o.id = p_org AND NOT o.automation_paused;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'automation paused' USING ERRCODE = '23514';
  END IF;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'telegram_d0.enabled');
  RETURN true;
END $$;
ALTER FUNCTION private.enable_telegram_d0(uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.enable_telegram_d0(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.enable_telegram_d0(uuid) TO app_api;

-- Finish a real attempt without fabricating a synthetic channel message.
CREATE FUNCTION private.finish_telegram_dispatch(
  p_org uuid, p_intent uuid, p_outcome text, p_message_id text
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_intent app.outbound_intents%ROWTYPE; v_state text;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org)
     OR p_outcome NOT IN ('accepted', 'rejected', 'unknown') THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_intent FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'intent not found' USING ERRCODE = 'P0002'; END IF;
  IF v_intent.status <> 'dispatching' THEN RETURN v_intent.status; END IF;
  v_state := p_outcome;
  UPDATE app.outbound_intents i SET status = v_state, updated_at = now(),
    external_message_id = CASE WHEN v_state = 'accepted' THEN p_message_id ELSE NULL END,
    error_code = CASE WHEN v_state = 'unknown' THEN 'CONFIRMATION_LOST'
      WHEN v_state = 'rejected' THEN 'PROVEN_REJECTION' ELSE NULL END
    WHERE i.organization_id = p_org AND i.id = p_intent;
  UPDATE app.delivery_attempts a SET state = v_state, finished_at = now(),
    external_message_id = CASE WHEN v_state = 'accepted' THEN p_message_id ELSE NULL END,
    error_code = CASE WHEN v_state = 'unknown' THEN 'CONFIRMATION_LOST'
      WHEN v_state = 'rejected' THEN 'PROVEN_REJECTION' ELSE NULL END
    WHERE a.organization_id = p_org AND a.intent_id = p_intent AND a.state = 'dispatching';
  IF v_state = 'unknown' THEN
    INSERT INTO app.delivery_incidents(organization_id, intent_id, reason, next_action)
      VALUES (p_org, p_intent, 'confirmation_lost',
        'Verificar o Telegram antes de qualquer nova ação. Não reenviar esta intenção.')
      ON CONFLICT (organization_id, intent_id) DO NOTHING;
  END IF;
  RETURN v_state;
END $$;
ALTER FUNCTION private.finish_telegram_dispatch(uuid,uuid,text,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.finish_telegram_dispatch(uuid,uuid,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.finish_telegram_dispatch(uuid,uuid,text,text) TO app_api;
