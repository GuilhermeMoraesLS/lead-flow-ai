CREATE POLICY seller_gestor_update ON app.sellers FOR UPDATE TO app_api
USING (organization_id = (SELECT private.org_id()) AND EXISTS (
  SELECT 1 FROM app.org_members m WHERE m.organization_id = sellers.organization_id
    AND m.user_id = (SELECT private.actor_id()) AND m.role = 'gestor' AND m.status = 'active'
))
WITH CHECK (organization_id = (SELECT private.org_id()) AND EXISTS (
  SELECT 1 FROM app.org_members m WHERE m.organization_id = sellers.organization_id
    AND m.user_id = (SELECT private.actor_id()) AND m.role = 'gestor' AND m.status = 'active'
));
GRANT UPDATE (active, available) ON app.sellers TO app_api;
