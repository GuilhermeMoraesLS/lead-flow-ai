CREATE TABLE app.contact_opt_outs (
  organization_id uuid NOT NULL,
  channel_id uuid NOT NULL,
  lead_id uuid NOT NULL,
  source_event_id uuid NOT NULL,
  source_conversation_id uuid NOT NULL,
  reason text NOT NULL CHECK (reason = 'explicit_stop_request'),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, channel_id, lead_id),
  FOREIGN KEY (organization_id, channel_id) REFERENCES app.channels(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, lead_id) REFERENCES app.leads(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, source_event_id) REFERENCES app.inbound_events(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, source_conversation_id) REFERENCES app.conversations(organization_id, id) ON DELETE RESTRICT
);
CREATE INDEX contact_opt_outs_source_event ON app.contact_opt_outs(organization_id, source_event_id);
ALTER TABLE app.contact_opt_outs ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.contact_opt_outs FORCE ROW LEVEL SECURITY;
CREATE POLICY contact_opt_outs_team_read ON app.contact_opt_outs FOR SELECT TO app_api
  USING (organization_id = (SELECT private.org_id()) AND EXISTS (
    SELECT 1 FROM app.org_members m WHERE m.organization_id = contact_opt_outs.organization_id
      AND m.user_id = (SELECT private.actor_id()) AND m.status = 'active'
      AND (m.role = 'gestor' OR (m.role = 'vendedor' AND m.password_changed))));
CREATE POLICY contact_opt_outs_ingest ON app.contact_opt_outs TO app_bootstrap
  USING (true) WITH CHECK (true);
GRANT SELECT ON app.contact_opt_outs TO app_api;
GRANT SELECT, INSERT ON app.contact_opt_outs TO app_bootstrap;

-- All inbound writes take the same organization lock as the sender before touching a conversation.
CREATE FUNCTION private.receive_test_event_serialized(
  p_channel uuid, p_token_hash text, p_event_type text, p_event text,
  p_message text, p_chat text, p_user text, p_name text, p_body text,
  p_occurred timestamptz, p_sequence text
) RETURNS TABLE(organization_id uuid, conversation_id uuid, outbox_id uuid, duplicate boolean, status text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_org uuid;
BEGIN
  SELECT c.organization_id INTO v_org FROM app.channels c
    WHERE c.id = p_channel AND c.token_hash = p_token_hash;
  IF v_org IS NULL THEN
    RAISE EXCEPTION 'invalid channel token' USING ERRCODE = '28000';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = v_org FOR UPDATE;
  RETURN QUERY SELECT r.organization_id, r.conversation_id, r.outbox_id, r.duplicate, r.status
    FROM private.receive_test_event(p_channel, p_token_hash, p_event_type, p_event,
      p_message, p_chat, p_user, p_name, p_body, p_occurred, p_sequence) r;
END $$;
ALTER FUNCTION private.receive_test_event_serialized(uuid,text,text,text,text,text,text,text,text,timestamptz,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.receive_test_event_serialized(uuid,text,text,text,text,text,text,text,text,timestamptz,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.receive_test_event_serialized(uuid,text,text,text,text,text,text,text,text,timestamptz,text) TO app_api;
REVOKE EXECUTE ON FUNCTION private.receive_test_event(uuid,text,text,text,text,text,text,text,text,timestamptz,text) FROM app_api;

CREATE FUNCTION private.keep_contact_opt_out()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM app.contact_opt_outs o WHERE o.organization_id = NEW.organization_id
    AND o.channel_id = NEW.channel_id AND o.lead_id = NEW.lead_id) THEN
    NEW.contact_blocked := true;
  END IF;
  RETURN NEW;
END $$;
ALTER FUNCTION private.keep_contact_opt_out() OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.keep_contact_opt_out() FROM PUBLIC;
CREATE TRIGGER keep_contact_opt_out BEFORE INSERT OR UPDATE OF contact_blocked ON app.conversations
  FOR EACH ROW EXECUTE FUNCTION private.keep_contact_opt_out();

CREATE FUNCTION private.apply_test_opt_out(p_channel uuid, p_token_hash text, p_external_event text)
RETURNS TABLE(source_event_id uuid, pending_attempts integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_org uuid; v_event app.inbound_events%ROWTYPE; v_conversation app.conversations%ROWTYPE;
  v_source uuid; v_pending integer; v_owner uuid; v_incident uuid;
BEGIN
  SELECT c.organization_id INTO v_org FROM app.channels c
    WHERE c.id = p_channel AND c.token_hash = p_token_hash;
  IF v_org IS NULL THEN
    RAISE EXCEPTION 'invalid channel token' USING ERRCODE = '28000';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = v_org FOR UPDATE;
  SELECT * INTO v_event FROM app.inbound_events e WHERE e.organization_id = v_org
    AND e.channel_id = p_channel AND e.external_event_id = p_external_event
    AND e.event_type = 'message' AND e.processing_status = 'recorded';
  IF NOT FOUND OR v_event.conversation_id IS NULL THEN
    RAISE EXCEPTION 'recorded message required' USING ERRCODE = 'P0002';
  END IF;
  SELECT * INTO v_conversation FROM app.conversations c WHERE c.organization_id = v_org
    AND c.id = v_event.conversation_id FOR UPDATE;
  INSERT INTO app.contact_opt_outs(organization_id, channel_id, lead_id,
    source_event_id, source_conversation_id, reason)
    VALUES (v_org, p_channel, v_conversation.lead_id, v_event.id,
      v_conversation.id, 'explicit_stop_request')
    ON CONFLICT (organization_id, channel_id, lead_id) DO NOTHING;
  SELECT o.source_event_id INTO v_source FROM app.contact_opt_outs o
    WHERE o.organization_id = v_org AND o.channel_id = p_channel
      AND o.lead_id = v_conversation.lead_id;
  UPDATE app.conversations c SET contact_blocked = true,
    control_version = c.control_version + CASE WHEN c.contact_blocked THEN 0 ELSE 1 END
    WHERE c.organization_id = v_org AND c.channel_id = p_channel
      AND c.lead_id = v_conversation.lead_id AND NOT c.contact_blocked;
  UPDATE app.outbound_intents i SET status = 'cancelled',
    cancellation_reason = 'opt_out', updated_at = now()
    FROM app.conversations c WHERE i.organization_id = v_org
      AND i.organization_id = c.organization_id AND i.conversation_id = c.id
      AND c.channel_id = p_channel AND c.lead_id = v_conversation.lead_id
      AND i.kind = 'synthetic_auto' AND i.status = 'pending';
  SELECT count(*) INTO v_pending FROM app.outbound_intents i
    JOIN app.conversations c ON c.organization_id = i.organization_id
      AND c.id = i.conversation_id
    WHERE i.organization_id = v_org AND c.channel_id = p_channel
      AND c.lead_id = v_conversation.lead_id AND i.kind = 'synthetic_auto'
      AND i.status = 'dispatching';
  IF v_conversation.mode = 'automatic' THEN
    UPDATE app.conversations c SET mode = 'awaiting_human',
      handoff_reason = 'opt_out', handoff_requested_at = now(), summary_status = 'unavailable',
      control_version = c.control_version + 1
      WHERE c.organization_id = v_org AND c.id = v_conversation.id;
    IF NOT EXISTS (SELECT 1 FROM app.operation_incidents i WHERE i.organization_id = v_org
      AND i.conversation_id = v_conversation.id AND i.state = 'open') THEN
      SELECT m.user_id INTO v_owner FROM app.org_members m WHERE m.organization_id = v_org
        AND m.role = 'gestor' AND m.status = 'active' ORDER BY m.created_at, m.user_id LIMIT 1;
      IF v_owner IS NULL THEN
        RAISE EXCEPTION 'no queue owner' USING ERRCODE = '42501';
      END IF;
      INSERT INTO app.operation_incidents(organization_id, conversation_id, cause_event_id,
        kind, reason, owner_member_id, next_action)
        VALUES (v_org, v_conversation.id, v_event.id, 'human_handoff', 'opt_out',
          v_owner, 'Verificar pedido de parada e atender manualmente; não reativar automação.')
        RETURNING id INTO v_incident;
      INSERT INTO app.outbox_events(organization_id, event_type, aggregate_id, dedupe_key)
        VALUES (v_org, 'handoff.requested', v_conversation.id, 'handoff:' || v_event.id::text);
      INSERT INTO app.audit_events(organization_id, actor_id, action)
        VALUES (v_org, v_owner, 'contact.opted_out');
    END IF;
  END IF;
  RETURN QUERY SELECT v_source, v_pending;
END $$;
ALTER FUNCTION private.apply_test_opt_out(uuid,text,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.apply_test_opt_out(uuid,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.apply_test_opt_out(uuid,text,text) TO app_api;

CREATE OR REPLACE FUNCTION private.set_test_contact_block(
  p_org uuid, p_conversation uuid, p_blocked boolean
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_version integer;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'control forbidden' USING ERRCODE = '42501';
  END IF;
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  IF NOT p_blocked AND EXISTS (SELECT 1 FROM app.conversations c
    JOIN app.contact_opt_outs o ON o.organization_id = c.organization_id
      AND o.channel_id = c.channel_id AND o.lead_id = c.lead_id
    WHERE c.organization_id = p_org AND c.id = p_conversation) THEN
    RAISE EXCEPTION 'contact opted out' USING ERRCODE = '23514';
  END IF;
  UPDATE app.conversations c SET contact_blocked = p_blocked,
    control_version = c.control_version + 1
    WHERE c.organization_id = p_org AND c.id = p_conversation
    RETURNING c.control_version INTO v_version;
  IF v_version IS NULL THEN
    RAISE EXCEPTION 'conversation not found' USING ERRCODE = 'P0002';
  END IF;
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, private.actor_id(), 'test_contact_block.changed');
  RETURN v_version;
END $$;
ALTER FUNCTION private.set_test_contact_block(uuid,uuid,boolean) OWNER TO app_bootstrap;
