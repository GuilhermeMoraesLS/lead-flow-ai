"""Checksum-verified, transactional forward migrations. No implicit reset."""

from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def migrate(conn, through=None):
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(17300901)")
        conn.execute("""CREATE TABLE IF NOT EXISTS public.leadflow_schema_migrations (
            name text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now()
        )""")
        for path in sorted((ROOT / "supabase/migrations").glob("*.sql")):
            if through and path.name > through:
                break
            content = path.read_bytes()
            digest = sha256(content).hexdigest()
            previous = conn.execute(
                "SELECT sha256 FROM public.leadflow_schema_migrations WHERE name=%s",
                (path.name,),
            ).fetchone()
            if previous:
                if previous[0] != digest:
                    raise RuntimeError("Applied migration changed: " + path.name)
                continue
            conn.execute(content.decode("utf-8"))
            conn.execute(
                "INSERT INTO public.leadflow_schema_migrations(name,sha256) VALUES(%s,%s)",
                (path.name, digest),
            )
