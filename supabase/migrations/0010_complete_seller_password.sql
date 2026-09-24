CREATE FUNCTION private.complete_seller_password(p_org uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() THEN
    RAISE EXCEPTION 'organization mismatch' USING ERRCODE = '42501';
  END IF;
  UPDATE app.org_members
     SET password_changed = true
   WHERE organization_id = p_org AND user_id = private.actor_id()
     AND role = 'vendedor' AND status = 'active' AND NOT password_changed;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'active pending seller not found' USING ERRCODE = 'P0002';
  END IF;
END $$;
ALTER FUNCTION private.complete_seller_password(uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.complete_seller_password(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.complete_seller_password(uuid) TO app_api;
