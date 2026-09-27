-- A revoked snapshot remains in history; only the current catalog is unique.
CREATE UNIQUE INDEX products_current_name_unique
  ON app.products (organization_id, lower(btrim(name)))
  WHERE status = 'ready';
