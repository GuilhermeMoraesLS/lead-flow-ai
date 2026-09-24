CREATE TABLE app.idempotency_keys (
  actor_id uuid NOT NULL,
  operation text NOT NULL,
  key text NOT NULL CHECK (length(key) BETWEEN 1 AND 255),
  request_hash text NOT NULL,
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (actor_id, operation, key)
);
ALTER TABLE app.idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.idempotency_keys FORCE ROW LEVEL SECURITY;
CREATE POLICY idempotency_actor ON app.idempotency_keys FOR SELECT TO app_api
USING (actor_id = (SELECT private.actor_id()));
CREATE POLICY idempotency_bootstrap ON app.idempotency_keys TO app_bootstrap
USING (true) WITH CHECK (true);
GRANT SELECT ON app.idempotency_keys TO app_api;
GRANT SELECT, INSERT ON app.idempotency_keys TO app_bootstrap;

CREATE OR REPLACE FUNCTION private.create_organization(
  p_name text, p_key text, p_request_hash text
) RETURNS TABLE (organization_id uuid, created boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  actor uuid := private.actor_id();
  existing_hash text;
  existing_org uuid;
BEGIN
  IF actor IS NULL THEN
    RAISE EXCEPTION 'authentication required' USING ERRCODE = '42501';
  END IF;
  SELECT request_hash, idempotency_keys.organization_id INTO existing_hash, existing_org
    FROM app.idempotency_keys
   WHERE actor_id = actor AND operation = 'organization.create' AND key = p_key
   FOR UPDATE;
  IF existing_org IS NOT NULL THEN
    IF existing_hash <> p_request_hash THEN
      RAISE EXCEPTION 'idempotency key reused with a different request'
        USING ERRCODE = '22000';
    END IF;
    organization_id := existing_org; created := false; RETURN NEXT; RETURN;
  END IF;
  INSERT INTO app.organizations(name, created_by) VALUES (p_name, actor)
    RETURNING id INTO organization_id;
  INSERT INTO app.org_members(organization_id, user_id, role)
    VALUES (organization_id, actor, 'gestor');
  INSERT INTO app.agents(organization_id) VALUES (organization_id);
  INSERT INTO app.audit_events(organization_id, actor_id, action)
    VALUES (organization_id, actor, 'organization.created');
  INSERT INTO app.idempotency_keys(actor_id, operation, key, request_hash, organization_id)
    VALUES (actor, 'organization.create', p_key, p_request_hash, organization_id);
  created := true; RETURN NEXT;
END $$;
ALTER FUNCTION private.create_organization(text, text, text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.create_organization(text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.create_organization(text, text, text) TO app_api;
