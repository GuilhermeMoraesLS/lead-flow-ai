ALTER FUNCTION private.receive_test_event(uuid,text,text,text,text,text,text,text,text,timestamptz,text)
  RESET plpgsql.variable_conflict;

CREATE OR REPLACE FUNCTION private.receive_test_event(
  p_channel uuid, p_token_hash text, p_event_type text, p_event text,
  p_message text, p_chat text, p_user text, p_name text, p_body text,
  p_occurred timestamptz, p_sequence text
) RETURNS TABLE(organization_id uuid, conversation_id uuid, outbox_id uuid, duplicate boolean, status text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
#variable_conflict use_column
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
