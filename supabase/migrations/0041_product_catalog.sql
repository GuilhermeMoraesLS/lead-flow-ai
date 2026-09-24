-- A current row points to immutable snapshots. The organization revision serializes
-- catalog writes and gives later response preparation one freshness check.
ALTER TABLE app.organizations
  ADD COLUMN commercial_revision bigint NOT NULL DEFAULT 1 CHECK (commercial_revision > 0);

CREATE POLICY commercial_revision_gestor ON app.organizations FOR UPDATE TO app_api
  USING (id = (SELECT private.org_id()) AND (SELECT private.gestor_of(id)))
  WITH CHECK (id = (SELECT private.org_id()) AND (SELECT private.gestor_of(id)));
GRANT UPDATE (commercial_revision) ON app.organizations TO app_api;

CREATE TABLE app.products (
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 120),
  price numeric(20,4) CHECK (price >= 0),
  available boolean NOT NULL,
  status text NOT NULL DEFAULT 'ready' CHECK (status IN ('ready', 'revoked')),
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  commercial_revision bigint NOT NULL CHECK (commercial_revision > 0),
  created_by uuid NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE app.product_versions (
  organization_id uuid NOT NULL,
  product_id uuid NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  commercial_revision bigint NOT NULL CHECK (commercial_revision > 0),
  name text NOT NULL,
  price numeric(20,4),
  available boolean NOT NULL,
  status text NOT NULL CHECK (status IN ('ready', 'revoked')),
  recorded_by uuid NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, product_id, version),
  FOREIGN KEY (organization_id, product_id)
    REFERENCES app.products(organization_id, id) ON DELETE RESTRICT
);

ALTER TABLE app.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.products FORCE ROW LEVEL SECURITY;
ALTER TABLE app.product_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.product_versions FORCE ROW LEVEL SECURITY;

CREATE POLICY products_manager_select ON app.products FOR SELECT TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY products_manager_insert ON app.products FOR INSERT TO app_api
  WITH CHECK (organization_id = (SELECT private.org_id())
    AND created_by = (SELECT private.actor_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY products_manager_update ON app.products FOR UPDATE TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)))
  WITH CHECK (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY product_versions_manager_select ON app.product_versions FOR SELECT TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY product_versions_manager_insert ON app.product_versions FOR INSERT TO app_api
  WITH CHECK (organization_id = (SELECT private.org_id())
    AND recorded_by = (SELECT private.actor_id())
    AND (SELECT private.gestor_of(organization_id)));

GRANT SELECT, INSERT ON app.products, app.product_versions TO app_api;
GRANT UPDATE (name, price, available, status, version, commercial_revision, updated_at)
  ON app.products TO app_api;
