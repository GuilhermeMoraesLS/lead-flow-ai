-- The worker only receives batch IDs for explicitly activated organizations.
CREATE FUNCTION private.worker_telegram_due()
RETURNS TABLE(batch_id uuid) LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
  SELECT b.id FROM app.telegram_message_batches b
  JOIN app.organizations o ON o.id = b.organization_id
  WHERE b.status = 'ready' AND o.d0_enabled
  ORDER BY b.created_at, b.id LIMIT 100
$$;
ALTER FUNCTION private.worker_telegram_due() OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.worker_telegram_due() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.worker_telegram_due() TO app_worker;
GRANT SELECT ON app.telegram_message_batches TO app_bootstrap;
CREATE POLICY telegram_batches_bootstrap_read ON app.telegram_message_batches
  FOR SELECT TO app_bootstrap USING (true);
