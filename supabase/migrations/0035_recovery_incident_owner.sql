ALTER TABLE app.delivery_incidents ADD COLUMN owner_member_id uuid;
UPDATE app.delivery_incidents d SET owner_member_id = (
  SELECT m.user_id FROM app.org_members m WHERE m.organization_id = d.organization_id
    AND m.role = 'gestor' ORDER BY (m.status = 'active') DESC, m.created_at, m.user_id LIMIT 1
);
ALTER TABLE app.delivery_incidents
  ADD CONSTRAINT delivery_incident_owner_same_org FOREIGN KEY (organization_id, owner_member_id)
    REFERENCES app.org_members(organization_id, user_id) ON DELETE RESTRICT;

CREATE FUNCTION private.assign_delivery_incident_owner()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF NEW.owner_member_id IS NULL THEN
    SELECT m.user_id INTO NEW.owner_member_id FROM app.org_members m
      WHERE m.organization_id = NEW.organization_id AND m.role = 'gestor'
        AND m.status = 'active' ORDER BY m.created_at, m.user_id LIMIT 1;
  END IF;
  IF NEW.owner_member_id IS NULL THEN
    RAISE EXCEPTION 'no incident owner' USING ERRCODE = '42501';
  END IF;
  RETURN NEW;
END $$;
ALTER FUNCTION private.assign_delivery_incident_owner() OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.assign_delivery_incident_owner() FROM PUBLIC;
CREATE TRIGGER assign_delivery_incident_owner BEFORE INSERT ON app.delivery_incidents
  FOR EACH ROW EXECUTE FUNCTION private.assign_delivery_incident_owner();
