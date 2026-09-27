-- A managed-bot callback can be delivered again with the same update_id.
-- Keep the claim with the organization row so concurrent deliveries serialize.
ALTER TABLE app.telegram_provisioning
  ADD COLUMN last_managed_update_id bigint;
