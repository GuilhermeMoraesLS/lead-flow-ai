-- SL-11: private manager documents, versioned ingestion and one fixed embedding profile.
-- Objects live outside the database; rows keep only their organization-scoped key and hash.
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

CREATE TABLE app.knowledge_documents (
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 200),
  active_version_id uuid,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE app.knowledge_uploads (
  organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE RESTRICT,
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  document_id uuid,
  filename text NOT NULL CHECK (length(btrim(filename)) BETWEEN 1 AND 200),
  media_type text NOT NULL CHECK (media_type IN ('pdf', 'docx', 'txt', 'md')),
  declared_size integer NOT NULL CHECK (declared_size BETWEEN 1 AND 10485760),
  token_hash text NOT NULL CHECK (token_hash ~ '^[0-9a-f]{64}$'),
  expires_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'received', 'submitted')),
  object_sha256 text CHECK (object_sha256 ~ '^[0-9a-f]{64}$'),
  received_size integer CHECK (received_size BETWEEN 1 AND 10485760),
  version_id uuid,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, document_id)
    REFERENCES app.knowledge_documents(organization_id, id) ON DELETE RESTRICT
);

CREATE TABLE app.knowledge_versions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL,
  upload_id uuid NOT NULL,
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  embedding_profile text NOT NULL
    CHECK (embedding_profile = 'openai:text-embedding-3-small:1536'),
  media_type text NOT NULL CHECK (media_type IN ('pdf', 'docx', 'txt', 'md')),
  size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 1 AND 10485760),
  object_key text NOT NULL,
  status text NOT NULL DEFAULT 'uploaded' CHECK (status IN
    ('uploaded', 'validating', 'extracting', 'embedding', 'ready', 'failed')),
  parser_version text,
  error_code text,
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  claim_token uuid,
  lease_until timestamptz,
  chunk_count integer CHECK (chunk_count > 0),
  embedding_tokens integer CHECK (embedding_tokens >= 0),
  estimated_cost_usd numeric(12,6) CHECK (estimated_cost_usd >= 0),
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  ready_at timestamptz,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, document_id, content_hash, embedding_profile),
  CHECK ((status = 'ready') = (ready_at IS NOT NULL AND chunk_count IS NOT NULL)),
  CHECK ((status = 'failed') = (error_code IS NOT NULL)),
  FOREIGN KEY (organization_id, document_id)
    REFERENCES app.knowledge_documents(organization_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (organization_id, upload_id)
    REFERENCES app.knowledge_uploads(organization_id, id) ON DELETE RESTRICT
);
CREATE INDEX knowledge_versions_due ON app.knowledge_versions(created_at, id)
  WHERE status IN ('uploaded', 'validating', 'extracting', 'embedding');
CREATE INDEX knowledge_versions_content ON app.knowledge_versions(organization_id, content_hash);

ALTER TABLE app.knowledge_documents ADD CONSTRAINT knowledge_documents_active_version
  FOREIGN KEY (organization_id, active_version_id)
  REFERENCES app.knowledge_versions(organization_id, id) ON DELETE RESTRICT;
ALTER TABLE app.knowledge_uploads ADD CONSTRAINT knowledge_uploads_version
  FOREIGN KEY (organization_id, version_id)
  REFERENCES app.knowledge_versions(organization_id, id) ON DELETE RESTRICT;

-- The column type fixes the dimension; mixing profiles in one collection is rejected.
CREATE TABLE app.knowledge_chunks (
  organization_id uuid NOT NULL,
  version_id uuid NOT NULL,
  ordinal integer NOT NULL CHECK (ordinal >= 0),
  location text NOT NULL CHECK (length(location) BETWEEN 1 AND 300),
  body text NOT NULL CHECK (length(body) BETWEEN 1 AND 4000),
  embedding public.vector(1536) NOT NULL,
  PRIMARY KEY (organization_id, version_id, ordinal),
  FOREIGN KEY (organization_id, version_id)
    REFERENCES app.knowledge_versions(organization_id, id) ON DELETE RESTRICT
);

ALTER TABLE app.knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.knowledge_documents FORCE ROW LEVEL SECURITY;
ALTER TABLE app.knowledge_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.knowledge_uploads FORCE ROW LEVEL SECURITY;
ALTER TABLE app.knowledge_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.knowledge_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE app.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.knowledge_chunks FORCE ROW LEVEL SECURITY;

CREATE POLICY knowledge_documents_manager ON app.knowledge_documents TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)))
  WITH CHECK (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY knowledge_uploads_manager ON app.knowledge_uploads TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)))
  WITH CHECK (organization_id = (SELECT private.org_id())
    AND created_by = (SELECT private.actor_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY knowledge_versions_manager ON app.knowledge_versions TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)))
  WITH CHECK (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));
CREATE POLICY knowledge_chunks_manager ON app.knowledge_chunks FOR SELECT TO app_api
  USING (organization_id = (SELECT private.org_id())
    AND (SELECT private.gestor_of(organization_id)));

CREATE POLICY knowledge_documents_worker ON app.knowledge_documents TO app_worker
  USING (true) WITH CHECK (true);
CREATE POLICY knowledge_versions_worker ON app.knowledge_versions TO app_worker
  USING (true) WITH CHECK (true);
CREATE POLICY knowledge_chunks_worker ON app.knowledge_chunks TO app_worker
  USING (true) WITH CHECK (true);

GRANT SELECT, INSERT ON app.knowledge_documents, app.knowledge_uploads,
  app.knowledge_versions TO app_api;
GRANT UPDATE (status, object_sha256, received_size, version_id)
  ON app.knowledge_uploads TO app_api;
GRANT UPDATE (status, error_code, attempts, claim_token, lease_until, updated_at)
  ON app.knowledge_versions TO app_api;
GRANT SELECT ON app.knowledge_chunks TO app_api;

GRANT SELECT ON app.knowledge_documents, app.knowledge_versions TO app_worker;
GRANT UPDATE (active_version_id) ON app.knowledge_documents TO app_worker;
GRANT UPDATE (status, parser_version, error_code, attempts, claim_token, lease_until,
  chunk_count, embedding_tokens, estimated_cost_usd, updated_at, ready_at)
  ON app.knowledge_versions TO app_worker;
GRANT SELECT, INSERT ON app.knowledge_chunks TO app_worker;
