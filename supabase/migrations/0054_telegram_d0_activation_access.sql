-- The narrow activation function reads only prerequisites across forced RLS.
GRANT SELECT ON app.telegram_provisioning, app.products TO app_bootstrap;
CREATE POLICY telegram_provisioning_bootstrap_read
  ON app.telegram_provisioning FOR SELECT TO app_bootstrap USING (true);
CREATE POLICY products_bootstrap_read
  ON app.products FOR SELECT TO app_bootstrap USING (true);
