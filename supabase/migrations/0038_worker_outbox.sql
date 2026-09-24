-- The broker carries only IDs; the database remains the source of work and effects.
CREATE FUNCTION private.worker_due_outbox()
RETURNS TABLE(organization_id uuid, outbox_id uuid)
LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
  SELECT o.organization_id, o.id FROM app.outbox_events o
  WHERE o.published_at IS NULL AND o.available_at <= now()
  ORDER BY o.available_at, o.id LIMIT 100
$$;
ALTER FUNCTION private.worker_due_outbox() OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.worker_due_outbox() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.worker_due_outbox() TO app_worker;

CREATE FUNCTION private.worker_consume_outbox(p_org uuid, p_outbox uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_added integer;
BEGIN
  PERFORM 1 FROM app.organizations o WHERE o.id = p_org FOR UPDATE;
  IF NOT FOUND THEN
    RETURN false;
  END IF;
  PERFORM 1 FROM app.outbox_events o WHERE o.organization_id = p_org AND o.id = p_outbox FOR UPDATE;
  IF NOT FOUND THEN
    RETURN false;
  END IF;
  INSERT INTO app.outbox_effects(organization_id, outbox_id) VALUES (p_org, p_outbox)
    ON CONFLICT DO NOTHING;
  GET DIAGNOSTICS v_added = ROW_COUNT;
  UPDATE app.outbox_events o SET published_at = coalesce(o.published_at, now())
    WHERE o.organization_id = p_org AND o.id = p_outbox;
  RETURN v_added = 1;
END $$;
ALTER FUNCTION private.worker_consume_outbox(uuid,uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.worker_consume_outbox(uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.worker_consume_outbox(uuid,uuid) TO app_worker;
