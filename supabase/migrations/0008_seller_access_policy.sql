CREATE POLICY seller_bootstrap_read ON app.sellers FOR SELECT TO app_bootstrap USING (true);
