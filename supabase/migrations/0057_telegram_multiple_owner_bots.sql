-- One Telegram manager may own bots for multiple organizations. Only one
-- unassigned managed-bot callback can be pending for that manager at a time.
DROP INDEX app.telegram_provisioning_owner_pending;
CREATE UNIQUE INDEX telegram_provisioning_owner_pending
  ON app.telegram_provisioning(telegram_owner_id)
  WHERE status IN ('awaiting_bot', 'configuring');
ALTER TABLE app.telegram_provisioning
  DROP CONSTRAINT telegram_provisioning_telegram_owner_id_key;
