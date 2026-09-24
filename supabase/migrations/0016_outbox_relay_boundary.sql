-- Publication acknowledgement is a separate transaction from the consumer effect.
CREATE POLICY outbox_manager_publish ON app.outbox_events FOR UPDATE TO app_api
USING (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)))
WITH CHECK (organization_id = (SELECT private.org_id()) AND (SELECT private.gestor_of(organization_id)));
GRANT UPDATE (published_at) ON app.outbox_events TO app_api;

CREATE OR REPLACE FUNCTION private.consume_test_outbox(p_org uuid, p_outbox uuid)
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
  RETURN QUERY SELECT v_added = 1,
    (SELECT count(*) FROM app.outbox_effects e WHERE e.organization_id = p_org AND e.outbox_id = p_outbox);
END $$;
