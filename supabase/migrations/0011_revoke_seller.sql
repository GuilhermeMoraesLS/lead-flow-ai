CREATE FUNCTION private.revoke_seller(p_org uuid, p_seller uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'manager access required' USING ERRCODE = '42501';
  END IF;
  UPDATE app.org_members SET status = 'revoked'
   WHERE organization_id = p_org AND seller_id = p_seller
     AND role = 'vendedor' AND status = 'active';
  IF NOT FOUND THEN
    RAISE EXCEPTION 'active seller not found' USING ERRCODE = 'P0002';
  END IF;
END $$;
ALTER FUNCTION private.revoke_seller(uuid, uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.revoke_seller(uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.revoke_seller(uuid, uuid) TO app_api;
