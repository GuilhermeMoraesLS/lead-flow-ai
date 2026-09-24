-- Row locking an organization needs UPDATE privilege even though the row is unchanged.
GRANT UPDATE (id) ON app.organizations TO app_bootstrap;
