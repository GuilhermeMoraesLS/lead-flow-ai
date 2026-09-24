ALTER TABLE app.sellers
  ADD COLUMN email text,
  ADD COLUMN phone text,
  ADD CONSTRAINT seller_email_format CHECK (email IS NULL OR (length(email) <= 254 AND email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$')),
  ADD CONSTRAINT seller_phone_format CHECK (phone IS NULL OR phone ~ '^\+[1-9][0-9]{1,14}$');

CREATE UNIQUE INDEX seller_org_email ON app.sellers(organization_id, lower(email)) WHERE email IS NOT NULL;
