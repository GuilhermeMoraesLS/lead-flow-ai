ALTER TABLE app.agents
  ADD COLUMN name text NOT NULL DEFAULT '' CHECK (length(name) <= 120),
  ADD COLUMN identity text NOT NULL DEFAULT '' CHECK (length(identity) <= 500),
  ADD COLUMN instructions text NOT NULL DEFAULT '' CHECK (length(instructions) <= 10000);

CREATE POLICY agent_gestor_update ON app.agents FOR UPDATE TO app_api
USING (organization_id = (SELECT private.org_id()) AND EXISTS (
 SELECT 1 FROM app.org_members m WHERE m.organization_id = agents.organization_id
 AND m.user_id = (SELECT private.actor_id()) AND m.role = 'gestor' AND m.status = 'active'))
WITH CHECK (organization_id = (SELECT private.org_id()) AND EXISTS (
 SELECT 1 FROM app.org_members m WHERE m.organization_id = agents.organization_id
 AND m.user_id = (SELECT private.actor_id()) AND m.role = 'gestor' AND m.status = 'active'));

GRANT UPDATE (name, identity, instructions, version, updated_at) ON app.agents TO app_api;
