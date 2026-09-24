-- Runtime roles never own tables and never bypass RLS.
CREATE ROLE app_bootstrap NOLOGIN NOSUPERUSER NOBYPASSRLS;
CREATE SCHEMA app;
CREATE SCHEMA private;
REVOKE ALL ON SCHEMA app, private FROM PUBLIC;
GRANT USAGE ON SCHEMA app, private TO app_api, app_bootstrap;
ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA private REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

CREATE TABLE app.organizations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 120),
 created_by uuid NOT NULL,
 automation_enabled boolean NOT NULL DEFAULT false CHECK (NOT automation_enabled),
 version integer NOT NULL DEFAULT 1 CHECK (version > 0),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE app.org_members (
 organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
 user_id uuid NOT NULL,
 role text NOT NULL CHECK (role IN ('gestor', 'vendedor')),
 status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY (organization_id, user_id)
);
CREATE INDEX org_members_actor ON app.org_members(user_id, status, organization_id);
CREATE TABLE app.agents (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 organization_id uuid NOT NULL UNIQUE REFERENCES app.organizations(id) ON DELETE RESTRICT,
 active boolean NOT NULL DEFAULT false CHECK (NOT active),
 version integer NOT NULL DEFAULT 1 CHECK (version > 0),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (organization_id, id)
);
CREATE TABLE app.audit_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
 actor_id uuid NOT NULL,
 action text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);

CREATE FUNCTION private.actor_id() RETURNS uuid LANGUAGE sql STABLE
SET search_path = '' AS $$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $$;
CREATE FUNCTION private.org_id() RETURNS uuid LANGUAGE sql STABLE
SET search_path = '' AS $$ SELECT nullif(current_setting('app.organization_id', true), '')::uuid $$;
GRANT EXECUTE ON FUNCTION private.actor_id(), private.org_id() TO app_api, app_bootstrap;

ALTER TABLE app.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.organizations FORCE ROW LEVEL SECURITY;
ALTER TABLE app.org_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.org_members FORCE ROW LEVEL SECURITY;
ALTER TABLE app.agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.agents FORCE ROW LEVEL SECURITY;
ALTER TABLE app.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.audit_events FORCE ROW LEVEL SECURITY;

CREATE POLICY own_membership ON app.org_members FOR SELECT TO app_api
USING (user_id = (SELECT private.actor_id()) AND status = 'active'
 AND ((SELECT private.org_id()) IS NULL OR organization_id = (SELECT private.org_id())));
CREATE POLICY organization_member ON app.organizations FOR SELECT TO app_api
USING (id = (SELECT private.org_id()) AND EXISTS (
 SELECT 1 FROM app.org_members m WHERE m.organization_id = id));
CREATE POLICY agent_member ON app.agents FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND EXISTS (
 SELECT 1 FROM app.org_members m WHERE m.organization_id = agents.organization_id AND m.role = 'gestor'));
CREATE POLICY audit_member ON app.audit_events FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND EXISTS (
 SELECT 1 FROM app.org_members m WHERE m.organization_id = audit_events.organization_id AND m.role = 'gestor'));

-- The NOLOGIN role can only be used inside the narrow, trusted bootstrap function.
CREATE POLICY bootstrap_org ON app.organizations TO app_bootstrap USING (true) WITH CHECK (true);
CREATE POLICY bootstrap_member ON app.org_members TO app_bootstrap USING (true) WITH CHECK (true);
CREATE POLICY bootstrap_agent ON app.agents TO app_bootstrap USING (true) WITH CHECK (true);
CREATE POLICY bootstrap_audit ON app.audit_events TO app_bootstrap USING (true) WITH CHECK (true);
GRANT SELECT ON app.organizations, app.org_members, app.agents, app.audit_events TO app_api;
GRANT SELECT, INSERT ON app.organizations, app.org_members, app.agents, app.audit_events TO app_bootstrap;

CREATE FUNCTION private.create_organization(p_name text) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE actor uuid := private.actor_id(); org uuid;
BEGIN
 IF actor IS NULL THEN RAISE EXCEPTION 'authentication required' USING ERRCODE = '42501'; END IF;
 INSERT INTO app.organizations(name, created_by) VALUES (p_name, actor) RETURNING id INTO org;
 INSERT INTO app.org_members(organization_id, user_id, role) VALUES (org, actor, 'gestor');
 INSERT INTO app.agents(organization_id) VALUES (org);
 INSERT INTO app.audit_events(organization_id, actor_id, action) VALUES (org, actor, 'organization.created');
 RETURN org;
END $$;
ALTER FUNCTION private.create_organization(text) OWNER TO app_bootstrap;
REVOKE ALL ON FUNCTION private.create_organization(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.create_organization(text) TO app_api;

