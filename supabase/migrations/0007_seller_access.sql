ALTER TABLE app.sellers ADD COLUMN active boolean NOT NULL DEFAULT true;
ALTER TABLE app.org_members
  ADD COLUMN seller_id uuid,
  ADD COLUMN password_changed boolean NOT NULL DEFAULT true,
  ADD CONSTRAINT seller_same_organization FOREIGN KEY (organization_id, seller_id)
    REFERENCES app.sellers(organization_id, id) ON DELETE RESTRICT;
CREATE UNIQUE INDEX one_membership_per_seller ON app.org_members(organization_id, seller_id)
  WHERE seller_id IS NOT NULL;

GRANT SELECT ON app.sellers TO app_bootstrap;
GRANT UPDATE ON app.org_members TO app_bootstrap;

CREATE FUNCTION private.gestor_of(p_org uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT EXISTS (
    SELECT 1 FROM app.org_members m
    WHERE m.organization_id = p_org AND m.user_id = private.actor_id()
      AND m.role = 'gestor' AND m.status = 'active'
  )
$$;
ALTER FUNCTION private.gestor_of(uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.gestor_of(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.gestor_of(uuid) TO app_api;

CREATE POLICY manager_memberships ON app.org_members FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id())
  AND (SELECT private.gestor_of(organization_id)));

CREATE FUNCTION private.enable_seller(p_org uuid, p_seller uuid, p_user uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF p_org IS DISTINCT FROM private.org_id() OR NOT private.gestor_of(p_org) THEN
    RAISE EXCEPTION 'manager access required' USING ERRCODE = '42501';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM app.sellers s WHERE s.id = p_seller AND s.organization_id = p_org) THEN
    RAISE EXCEPTION 'seller not found' USING ERRCODE = 'P0002';
  END IF;
  INSERT INTO app.org_members(organization_id, user_id, role, status, seller_id, password_changed)
  VALUES (p_org, p_user, 'vendedor', 'active', p_seller, false);
END $$;
ALTER FUNCTION private.enable_seller(uuid, uuid, uuid) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.enable_seller(uuid, uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.enable_seller(uuid, uuid, uuid) TO app_api;
