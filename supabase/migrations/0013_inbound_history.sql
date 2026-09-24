-- Local simulated bindings; no provider credentials or hosted channel connection.
CREATE TABLE app.channels (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  kind text NOT NULL CHECK (kind IN ('telegram', 'whatsapp_evolution')),
  token_hash text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id), UNIQUE (organization_id, kind)
);
CREATE INDEX channels_organization ON app.channels(organization_id);

CREATE TABLE app.leads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  channel_id uuid NOT NULL,
  external_user_id text NOT NULL CHECK (length(external_user_id) BETWEEN 1 AND 256),
  name text,
  last_contact_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id),
  UNIQUE (organization_id, channel_id, external_user_id),
  FOREIGN KEY (organization_id, channel_id) REFERENCES app.channels(organization_id, id) ON DELETE RESTRICT
);

CREATE TABLE app.conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  lead_id uuid NOT NULL,
  channel_id uuid NOT NULL,
  external_chat_id text NOT NULL CHECK (length(external_chat_id) BETWEEN 1 AND 256),
  input_revision integer NOT NULL DEFAULT 0 CHECK (input_revision >= 0),
  last_inbound_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id),
  UNIQUE (organization_id, channel_id, external_chat_id, lead_id),
  FOREIGN KEY (organization_id, lead_id) REFERENCES app.leads(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, channel_id) REFERENCES app.channels(organization_id, id) ON DELETE RESTRICT
);
CREATE INDEX conversations_lead ON app.conversations(organization_id, lead_id);

CREATE TABLE app.messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  conversation_id uuid NOT NULL,
  channel_id uuid NOT NULL,
  external_message_id text NOT NULL CHECK (length(external_message_id) BETWEEN 1 AND 256),
  direction text NOT NULL DEFAULT 'inbound' CHECK (direction = 'inbound'),
  content_kind text NOT NULL DEFAULT 'text' CHECK (content_kind = 'text'),
  text text NOT NULL,
  occurred_at timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  provider_order text,
  UNIQUE (organization_id, id),
  UNIQUE (organization_id, channel_id, conversation_id, external_message_id),
  FOREIGN KEY (organization_id, conversation_id) REFERENCES app.conversations(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, channel_id) REFERENCES app.channels(organization_id, id) ON DELETE RESTRICT
);
CREATE INDEX messages_history ON app.messages(organization_id, conversation_id, received_at, id);

CREATE TABLE app.inbound_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  channel_id uuid NOT NULL,
  external_event_id text NOT NULL CHECK (length(external_event_id) BETWEEN 1 AND 256),
  event_type text NOT NULL CHECK (event_type IN ('message', 'connection', 'echo')),
  processing_status text NOT NULL CHECK (processing_status IN ('recorded', 'ignored')),
  conversation_id uuid,
  outbox_id uuid,
  received_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id),
  UNIQUE (organization_id, channel_id, external_event_id, event_type),
  FOREIGN KEY (organization_id, channel_id) REFERENCES app.channels(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, conversation_id) REFERENCES app.conversations(organization_id, id) ON DELETE RESTRICT
);

CREATE TABLE app.outbox_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  event_type text NOT NULL CHECK (event_type = 'inbound.recorded'),
  aggregate_id uuid NOT NULL,
  dedupe_key text NOT NULL,
  available_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz,
  UNIQUE (organization_id, id),
  UNIQUE (organization_id, dedupe_key),
  FOREIGN KEY (organization_id, aggregate_id) REFERENCES app.conversations(organization_id, id) ON DELETE RESTRICT
);
CREATE INDEX outbox_unpublished ON app.outbox_events(available_at, id) WHERE published_at IS NULL;
ALTER TABLE app.inbound_events ADD CONSTRAINT inbound_outbox_same_org
  FOREIGN KEY (organization_id, outbox_id) REFERENCES app.outbox_events(organization_id, id) ON DELETE RESTRICT;

-- Durable simulated consumer record. Repeated publication cannot repeat the effect.
CREATE TABLE app.outbox_effects (
  organization_id uuid NOT NULL,
  outbox_id uuid NOT NULL,
  consumed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, outbox_id),
  FOREIGN KEY (organization_id, outbox_id) REFERENCES app.outbox_events(organization_id, id) ON DELETE RESTRICT
);

ALTER TABLE app.channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.channels FORCE ROW LEVEL SECURITY;
ALTER TABLE app.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.leads FORCE ROW LEVEL SECURITY;
ALTER TABLE app.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.conversations FORCE ROW LEVEL SECURITY;
ALTER TABLE app.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.messages FORCE ROW LEVEL SECURITY;
ALTER TABLE app.inbound_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.inbound_events FORCE ROW LEVEL SECURITY;
ALTER TABLE app.outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.outbox_events FORCE ROW LEVEL SECURITY;
ALTER TABLE app.outbox_effects ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.outbox_effects FORCE ROW LEVEL SECURITY;

CREATE POLICY channels_manager_read ON app.channels FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY channels_manager_insert ON app.channels FOR INSERT TO app_api
WITH CHECK (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY leads_manager_read ON app.leads FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY conversations_manager_read ON app.conversations FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY messages_manager_read ON app.messages FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY outbox_manager_read ON app.outbox_events FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));

CREATE POLICY channels_ingest ON app.channels TO app_bootstrap USING (true) WITH CHECK (true);
CREATE POLICY leads_ingest ON app.leads TO app_bootstrap USING (true) WITH CHECK (true);
CREATE POLICY conversations_ingest ON app.conversations TO app_bootstrap USING (true) WITH CHECK (true);
CREATE POLICY messages_ingest ON app.messages TO app_bootstrap USING (true) WITH CHECK (true);
CREATE POLICY inbound_ingest ON app.inbound_events TO app_bootstrap USING (true) WITH CHECK (true);
CREATE POLICY outbox_ingest ON app.outbox_events TO app_bootstrap USING (true) WITH CHECK (true);
CREATE POLICY effects_ingest ON app.outbox_effects TO app_bootstrap USING (true) WITH CHECK (true);

GRANT SELECT, INSERT ON app.channels TO app_api;
GRANT SELECT ON app.leads, app.conversations, app.messages, app.outbox_events TO app_api;
GRANT SELECT ON app.channels TO app_bootstrap;
GRANT SELECT, INSERT, UPDATE ON app.leads, app.conversations, app.inbound_events, app.outbox_events TO app_bootstrap;
GRANT SELECT, INSERT ON app.messages, app.outbox_effects TO app_bootstrap;

CREATE FUNCTION private.receive_test_event(
  p_channel uuid, p_token_hash text, p_event_type text, p_event text,
  p_message text, p_chat text, p_user text, p_name text, p_body text,
  p_occurred timestamptz, p_sequence text
) RETURNS TABLE(organization_id uuid, conversation_id uuid, outbox_id uuid, duplicate boolean, status text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_org uuid; v_event uuid; v_lead uuid; v_conversation uuid; v_outbox uuid;
BEGIN
  SELECT c.organization_id INTO v_org FROM app.channels c
   WHERE c.id = p_channel AND c.token_hash = p_token_hash;
  IF v_org IS NULL THEN
    RAISE EXCEPTION 'invalid channel token' USING ERRCODE = '28000';
  END IF;
  INSERT INTO app.inbound_events(organization_id, channel_id, external_event_id, event_type, processing_status)
  VALUES (v_org, p_channel, p_event, p_event_type,
          CASE WHEN p_event_type = 'message' THEN 'recorded' ELSE 'ignored' END)
  ON CONFLICT (organization_id, channel_id, external_event_id, event_type) DO NOTHING
  RETURNING id INTO v_event;
  IF v_event IS NULL THEN
    RETURN QUERY SELECT e.organization_id, e.conversation_id, e.outbox_id, true, e.processing_status
      FROM app.inbound_events e WHERE e.organization_id = v_org AND e.channel_id = p_channel
        AND e.external_event_id = p_event AND e.event_type = p_event_type;
    RETURN;
  END IF;
  IF p_event_type <> 'message' THEN
    RETURN QUERY SELECT v_org, NULL::uuid, NULL::uuid, false, 'ignored'::text;
    RETURN;
  END IF;
  INSERT INTO app.leads(organization_id, channel_id, external_user_id, name)
  VALUES (v_org, p_channel, p_user, p_name)
  ON CONFLICT (organization_id, channel_id, external_user_id)
    DO UPDATE SET last_contact_at = now()
  RETURNING id INTO v_lead;
  INSERT INTO app.conversations(organization_id, lead_id, channel_id, external_chat_id,
                                input_revision, last_inbound_at)
  VALUES (v_org, v_lead, p_channel, p_chat, 1, now())
  ON CONFLICT (organization_id, channel_id, external_chat_id, lead_id)
    DO UPDATE SET input_revision = conversations.input_revision + 1, last_inbound_at = now()
  RETURNING id INTO v_conversation;
  INSERT INTO app.messages(organization_id, conversation_id, channel_id, external_message_id,
                           text, occurred_at, provider_order)
  VALUES (v_org, v_conversation, p_channel, p_message, p_body, p_occurred, p_sequence);
  INSERT INTO app.outbox_events(organization_id, event_type, aggregate_id, dedupe_key)
  VALUES (v_org, 'inbound.recorded', v_conversation, v_event::text)
  RETURNING id INTO v_outbox;
  UPDATE app.inbound_events SET conversation_id = v_conversation, outbox_id = v_outbox WHERE id = v_event;
  RETURN QUERY SELECT v_org, v_conversation, v_outbox, false, 'recorded'::text;
END $$;
ALTER FUNCTION private.receive_test_event(uuid,text,text,text,text,text,text,text,text,timestamptz,text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.receive_test_event(uuid,text,text,text,text,text,text,text,text,timestamptz,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.receive_test_event(uuid,text,text,text,text,text,text,text,text,timestamptz,text) TO app_api;

CREATE FUNCTION private.consume_test_outbox(p_org uuid, p_outbox uuid)
RETURNS TABLE(new_effect boolean, effect_count bigint)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_added integer;
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'manager access required' USING ERRCODE = '42501';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM app.outbox_events o WHERE o.organization_id = p_org AND o.id = p_outbox) THEN
    RAISE EXCEPTION 'outbox event not found' USING ERRCODE = 'P0002';
  END IF;
  INSERT INTO app.outbox_effects(organization_id, outbox_id) VALUES (p_org, p_outbox)
  ON CONFLICT DO NOTHING;
  GET DIAGNOSTICS v_added = ROW_COUNT;
  UPDATE app.outbox_events SET published_at = coalesce(published_at, now())
   WHERE organization_id = p_org AND id = p_outbox;
  RETURN QUERY SELECT v_added = 1,
    (SELECT count(*) FROM app.outbox_effects e WHERE e.organization_id = p_org AND e.outbox_id = p_outbox);
END $$;
ALTER FUNCTION private.consume_test_outbox(uuid,uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.consume_test_outbox(uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.consume_test_outbox(uuid,uuid) TO app_api;
