CREATE TABLE app.sellers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 120),
  available boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id)
);
CREATE INDEX sellers_organization ON app.sellers(organization_id);

ALTER TABLE app.sellers ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.sellers FORCE ROW LEVEL SECURITY;
CREATE POLICY seller_gestor_read ON app.sellers FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND EXISTS (
  SELECT 1 FROM app.org_members m WHERE m.organization_id = sellers.organization_id
  AND m.user_id = (SELECT private.actor_id()) AND m.role = 'gestor' AND m.status = 'active'
));
CREATE POLICY seller_gestor_create ON app.sellers FOR INSERT TO app_api
WITH CHECK (organization_id = (SELECT private.org_id()) AND EXISTS (
  SELECT 1 FROM app.org_members m WHERE m.organization_id = sellers.organization_id
  AND m.user_id = (SELECT private.actor_id()) AND m.role = 'gestor' AND m.status = 'active'
));
GRANT SELECT, INSERT ON app.sellers TO app_api;
