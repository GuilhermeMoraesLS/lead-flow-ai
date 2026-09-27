-- The recovery worker needs schema visibility in addition to table grants.
GRANT USAGE ON SCHEMA app TO app_worker;
