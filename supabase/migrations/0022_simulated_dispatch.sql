CREATE TABLE app.delivery_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  intent_id uuid NOT NULL,
  attempt_no integer NOT NULL DEFAULT 1 CHECK (attempt_no = 1),
  state text NOT NULL CHECK (state IN ('dispatching', 'accepted', 'rejected', 'unknown')),
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  external_message_id text,
  error_code text,
  UNIQUE (organization_id, intent_id, attempt_no),
  FOREIGN KEY (organization_id, intent_id)
    REFERENCES app.outbound_intents(organization_id, id) ON DELETE RESTRICT
);
CREATE TABLE app.test_channel_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  channel_id uuid NOT NULL,
  intent_id uuid NOT NULL,
  external_message_id text NOT NULL UNIQUE,
  text text NOT NULL,
  accepted_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, intent_id),
  FOREIGN KEY (organization_id, channel_id)
    REFERENCES app.channels(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, intent_id)
    REFERENCES app.outbound_intents(organization_id, id) ON DELETE RESTRICT
);
CREATE INDEX test_channel_messages_channel ON app.test_channel_messages
  (organization_id, channel_id, accepted_at, id);
CREATE TABLE app.delivery_incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  intent_id uuid NOT NULL,
  reason text NOT NULL CHECK (reason = 'confirmation_lost'),
  state text NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'resolved')),
  next_action text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, intent_id),
  FOREIGN KEY (organization_id, intent_id)
    REFERENCES app.outbound_intents(organization_id, id) ON DELETE RESTRICT
);
ALTER TABLE app.delivery_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.delivery_attempts FORCE ROW LEVEL SECURITY;
ALTER TABLE app.test_channel_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.test_channel_messages FORCE ROW LEVEL SECURITY;
ALTER TABLE app.delivery_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.delivery_incidents FORCE ROW LEVEL SECURITY;
CREATE POLICY attempts_manager_read ON app.delivery_attempts FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY attempts_bootstrap ON app.delivery_attempts TO app_bootstrap
USING (true) WITH CHECK (true);
CREATE POLICY test_messages_manager_read ON app.test_channel_messages FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY test_messages_bootstrap ON app.test_channel_messages TO app_bootstrap
USING (true) WITH CHECK (true);
CREATE POLICY delivery_incidents_manager_read ON app.delivery_incidents FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY delivery_incidents_bootstrap ON app.delivery_incidents TO app_bootstrap
USING (true) WITH CHECK (true);
GRANT SELECT ON app.delivery_attempts, app.test_channel_messages TO app_api;
GRANT SELECT ON app.delivery_incidents TO app_api;
GRANT SELECT, INSERT, UPDATE ON app.delivery_attempts TO app_bootstrap;
GRANT SELECT, INSERT ON app.test_channel_messages TO app_bootstrap;
GRANT SELECT, INSERT, UPDATE ON app.delivery_incidents TO app_bootstrap;

CREATE FUNCTION private.start_test_dispatch(p_org uuid, p_intent uuid)
RETURNS TABLE(started boolean, current_status text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_intent app.outbound_intents%ROWTYPE; v_conversation app.conversations%ROWTYPE;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_intent FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'intent not found' USING ERRCODE = 'P0002';
  END IF;
  IF NOT private.gestor_of(p_org) AND private.actor_id() IS DISTINCT FROM v_intent.author_id THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  SELECT * INTO v_conversation FROM app.conversations c
    WHERE c.organization_id = p_org AND c.id = v_intent.conversation_id FOR UPDATE;
  SELECT * INTO v_intent FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent FOR UPDATE;
  IF v_intent.status <> 'pending' THEN
    RETURN QUERY SELECT false, v_intent.status;
    RETURN;
  END IF;
  IF v_conversation.mode <> 'human' OR
     v_conversation.claimed_by IS DISTINCT FROM v_intent.author_id OR
     NOT EXISTS (SELECT 1 FROM app.org_members m WHERE m.organization_id = p_org
       AND m.user_id = v_intent.author_id AND m.status = 'active'
       AND (m.role = 'gestor' OR (m.role = 'vendedor' AND m.password_changed
         AND m.seller_id = v_conversation.assigned_seller_id AND EXISTS (
           SELECT 1 FROM app.sellers s WHERE s.organization_id = p_org
             AND s.id = m.seller_id AND s.active AND s.available)))) THEN
    RAISE EXCEPTION 'sender no longer authorized' USING ERRCODE = '42501';
  END IF;
  IF EXISTS (SELECT 1 FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.conversation_id = v_intent.conversation_id
      AND i.status = 'dispatching') THEN
    RETURN QUERY SELECT false, 'pending'::text;
    RETURN;
  END IF;
  UPDATE app.outbound_intents i SET status = 'dispatching', updated_at = now()
    WHERE i.organization_id = p_org AND i.id = p_intent;
  INSERT INTO app.delivery_attempts(organization_id, intent_id, state)
    VALUES (p_org, p_intent, 'dispatching');
  RETURN QUERY SELECT true, 'dispatching'::text;
END $$;
ALTER FUNCTION private.start_test_dispatch(uuid,uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.start_test_dispatch(uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.start_test_dispatch(uuid,uuid) TO app_api;

CREATE FUNCTION private.finish_test_dispatch(p_org uuid, p_intent uuid, p_outcome text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_intent app.outbound_intents%ROWTYPE; v_state text; v_external text;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  SELECT * INTO v_intent FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'intent not found' USING ERRCODE = 'P0002';
  END IF;
  IF NOT private.gestor_of(p_org) AND private.actor_id() IS DISTINCT FROM v_intent.author_id THEN
    RAISE EXCEPTION 'dispatch forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.conversations c WHERE c.organization_id = p_org
    AND c.id = v_intent.conversation_id FOR UPDATE;
  SELECT * INTO v_intent FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.id = p_intent FOR UPDATE;
  IF v_intent.status <> 'dispatching' THEN
    RETURN v_intent.status;
  END IF;
  IF p_outcome = 'accepted' THEN v_state := 'accepted';
  ELSIF p_outcome = 'rejected' THEN v_state := 'rejected';
  ELSIF p_outcome = 'timeout_after_accept' THEN v_state := 'unknown';
  ELSE RAISE EXCEPTION 'invalid outcome' USING ERRCODE = '22023';
  END IF;
  IF p_outcome IN ('accepted', 'timeout_after_accept') THEN
    v_external := gen_random_uuid()::text;
    INSERT INTO app.test_channel_messages(
      organization_id, channel_id, intent_id, external_message_id, text
    ) VALUES (p_org, v_intent.channel_id, p_intent, v_external, v_intent.text);
  END IF;
  UPDATE app.outbound_intents i SET status = v_state, updated_at = now(),
    external_message_id = CASE WHEN v_state = 'accepted' THEN v_external ELSE NULL END,
    error_code = CASE WHEN v_state = 'rejected' THEN 'PROVEN_REJECTION'
      WHEN v_state = 'unknown' THEN 'CONFIRMATION_LOST' ELSE NULL END
    WHERE i.organization_id = p_org AND i.id = p_intent;
  UPDATE app.delivery_attempts a SET state = v_state, finished_at = now(),
    external_message_id = CASE WHEN v_state = 'accepted' THEN v_external ELSE NULL END,
    error_code = CASE WHEN v_state = 'rejected' THEN 'PROVEN_REJECTION'
      WHEN v_state = 'unknown' THEN 'CONFIRMATION_LOST' ELSE NULL END
    WHERE a.organization_id = p_org AND a.intent_id = p_intent AND a.attempt_no = 1;
  IF v_state = 'unknown' THEN
    INSERT INTO app.delivery_incidents(organization_id, intent_id, reason, next_action)
      VALUES (p_org, p_intent, 'confirmation_lost',
        'Verificar o envio no canal antes de qualquer nova ação. Não reenviar esta intenção.');
  END IF;
  RETURN v_state;
END $$;
ALTER FUNCTION private.finish_test_dispatch(uuid,uuid,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.finish_test_dispatch(uuid,uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.finish_test_dispatch(uuid,uuid,text) TO app_api;
