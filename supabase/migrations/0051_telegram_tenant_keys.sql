-- Enforce the tenant boundary across bot, inbox and sealed batch references.
ALTER TABLE app.telegram_provisioning
  ADD CONSTRAINT telegram_provisioning_org_bot UNIQUE (organization_id, bot_id);
ALTER TABLE app.telegram_message_buffer
  ADD CONSTRAINT telegram_buffer_org_bot FOREIGN KEY (organization_id, bot_id)
  REFERENCES app.telegram_provisioning(organization_id, bot_id) ON DELETE RESTRICT;
ALTER TABLE app.telegram_message_batches
  ADD CONSTRAINT telegram_batches_org_bot FOREIGN KEY (organization_id, bot_id)
  REFERENCES app.telegram_provisioning(organization_id, bot_id) ON DELETE RESTRICT;
ALTER TABLE app.telegram_message_batches
  ADD CONSTRAINT telegram_batches_identity UNIQUE (organization_id, id, bot_id, chat_id);
ALTER TABLE app.telegram_message_buffer
  ADD CONSTRAINT telegram_buffer_batch_chat FOREIGN KEY
  (organization_id, batch_id, bot_id, chat_id)
  REFERENCES app.telegram_message_batches(organization_id, id, bot_id, chat_id)
  ON DELETE RESTRICT;
