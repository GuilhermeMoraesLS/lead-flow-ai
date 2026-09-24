CREATE POLICY seller_self_read ON app.sellers FOR SELECT TO app_api
USING (organization_id = (SELECT private.org_id()) AND EXISTS (
  SELECT 1 FROM app.org_members m WHERE m.organization_id = sellers.organization_id
    AND m.seller_id = sellers.id AND m.user_id = (SELECT private.actor_id())
    AND m.role = 'vendedor' AND m.status = 'active'
));
