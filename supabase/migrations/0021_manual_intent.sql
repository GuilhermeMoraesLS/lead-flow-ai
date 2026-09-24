CREATE TABLE app.outbound_intents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  conversation_id uuid NOT NULL,
  channel_id uuid NOT NULL,
  command_id uuid NOT NULL,
  author_id uuid NOT NULL,
  text text NOT NULL CHECK (length(text) BETWEEN 1 AND 4096),
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'dispatching', 'accepted', 'rejected', 'unknown')),
  external_message_id text,
  error_code text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id),
  UNIQUE (organization_id, conversation_id, command_id),
  FOREIGN KEY (organization_id, conversation_id)
    REFERENCES app.conversations(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, channel_id)
    REFERENCES app.channels(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, author_id)
    REFERENCES app.org_members(organization_id, user_id) ON DELETE RESTRICT
);
CREATE INDEX outbound_conversation_history ON app.outbound_intents
  (organization_id, conversation_id, created_at, id);
CREATE UNIQUE INDEX one_dispatching_per_conversation ON app.outbound_intents
  (organization_id, conversation_id) WHERE status = 'dispatching';
ALTER TABLE app.outbound_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.outbound_intents FORCE ROW LEVEL SECURITY;
CREATE POLICY outbound_manager_read ON app.outbound_intents FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY outbound_seller_read ON app.outbound_intents FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND EXISTS (
  SELECT 1 FROM app.conversations c WHERE c.organization_id = outbound_intents.organization_id
    AND c.id = outbound_intents.conversation_id
    AND c.assigned_seller_id = (SELECT private.current_seller_id(outbound_intents.organization_id))));
CREATE POLICY outbound_bootstrap ON app.outbound_intents TO app_bootstrap
USING (true) WITH CHECK (true);
GRANT SELECT ON app.outbound_intents TO app_api;
GRANT SELECT, INSERT, UPDATE ON app.outbound_intents TO app_bootstrap;

ALTER TABLE app.outbox_events DROP CONSTRAINT outbox_events_event_type_check;
ALTER TABLE app.outbox_events ADD CONSTRAINT outbox_events_event_type_check
  CHECK (event_type IN ('inbound.recorded', 'handoff.requested', 'human_reply.requested'));

CREATE FUNCTION private.create_human_reply(
  p_org uuid, p_conversation uuid, p_version integer, p_command uuid, p_text text
) RETURNS TABLE(intent_id uuid, author_id uuid, status text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_conversation app.conversations%ROWTYPE; v_actor uuid := private.actor_id();
  v_existing app.outbound_intents%ROWTYPE;
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
  SELECT * INTO v_existing FROM app.outbound_intents i
    WHERE i.organization_id = p_org AND i.conversation_id = p_conversation
      AND i.command_id = p_command;
  IF FOUND THEN
    IF v_existing.author_id IS DISTINCT FROM v_actor OR v_existing.text <> p_text THEN
      RAISE EXCEPTION 'command mismatch' USING ERRCODE = '40001';
    END IF;
    RETURN QUERY SELECT v_existing.id, v_existing.author_id, v_existing.status;
    RETURN;
  END IF;
  IF v_conversation.control_version <> p_version OR v_conversation.mode <> 'human'
     OR v_conversation.claimed_by IS DISTINCT FROM v_actor THEN
    RAISE EXCEPTION 'conversation changed' USING ERRCODE = '40001';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM app.org_members m WHERE m.organization_id = p_org
    AND m.user_id = v_actor AND m.status = 'active'
    AND (m.role = 'gestor' OR (m.role = 'vendedor' AND m.password_changed
      AND m.seller_id = v_conversation.assigned_seller_id AND EXISTS (
        SELECT 1 FROM app.sellers s WHERE s.organization_id = p_org
        AND s.id = m.seller_id AND s.active AND s.available)))) THEN
    RAISE EXCEPTION 'reply forbidden' USING ERRCODE = '42501';
  END IF;
  IF length(p_text) < 1 OR length(p_text) > 4096 THEN
    RAISE EXCEPTION 'text too long' USING ERRCODE = '22001';
  END IF;
  INSERT INTO app.outbound_intents(
    organization_id, conversation_id, channel_id, command_id, author_id, text
  ) VALUES (p_org, p_conversation, v_conversation.channel_id, p_command, v_actor, p_text)
    RETURNING id INTO intent_id;
  INSERT INTO app.outbox_events(organization_id, event_type, aggregate_id, dedupe_key)
    VALUES (p_org, 'human_reply.requested', p_conversation, 'human_reply:' || intent_id::text);
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (p_org, v_actor, 'human_reply.requested');
  author_id := v_actor; status := 'pending';
  RETURN NEXT;
END $$;
ALTER FUNCTION private.create_human_reply(uuid,uuid,integer,uuid,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.create_human_reply(uuid,uuid,integer,uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.create_human_reply(uuid,uuid,integer,uuid,text) TO app_api;
