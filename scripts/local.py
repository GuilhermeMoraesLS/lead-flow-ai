"""Local synthetic SL-01 environment only. Never reads production credentials."""

import argparse
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ENV_FILE = ROOT / ".local" / "sl01.env"


def load_env():
    if not ENV_FILE.exists():
        raise SystemExit("Run scripts/local.py prepare first.")
    values = dict(line.split("=", 1) for line in ENV_FILE.read_text().splitlines() if line)
    os.environ.update(values)
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://app_api:"
        + values["LOCAL_APP_PASSWORD"]
        + "@127.0.0.1:54329/leadflow_sl01"
    )
    os.environ["AUTH_URL"] = "http://127.0.0.1:54321"
    os.environ["JWT_ISSUER"] = "http://127.0.0.1:54321/auth/v1"
    os.environ["APP_ENV"] = "local"
    if "LOCAL_REDIS_PASSWORD" in values:
        os.environ["CELERY_BROKER_URL"] = (
            "redis://:" + values["LOCAL_REDIS_PASSWORD"] + "@127.0.0.1:54330/0"
        )
    if "LOCAL_WORKER_PASSWORD" in values:
        os.environ["WORKER_DATABASE_URL"] = (
            "postgresql://app_worker:" + values["LOCAL_WORKER_PASSWORD"]
            + "@127.0.0.1:54329/leadflow_sl01"
        )
    os.environ["PYTHONPATH"] = str(ROOT / "apps/api/src") + os.pathsep + str(ROOT)
    return values


def admin_connection():
    values = load_env()
    return psycopg.connect(
        host="127.0.0.1",
        port=54329,
        dbname="leadflow_sl01",
        user="postgres",
        password=values["LOCAL_DB_PASSWORD"],
    )


def compose(*args):
    subprocess.run(["docker", "compose", "--env-file", str(ENV_FILE), *args], cwd=ROOT, check=True)


def prepare():
    ENV_FILE.parent.mkdir(exist_ok=True)
    if not ENV_FILE.exists():
        ENV_FILE.write_text(
            "".join(
                f"{key}={secrets.token_hex(32)}\n"
                for key in [
                    "LOCAL_DB_PASSWORD",
                    "LOCAL_AUTH_PASSWORD",
                    "LOCAL_APP_PASSWORD",
                    "LOCAL_JWT_SECRET",
                ]
            ),
            encoding="utf-8",
        )
    present = dict(line.split("=", 1) for line in ENV_FILE.read_text().splitlines() if line)
    if "LOCAL_REDIS_PASSWORD" not in present or "LOCAL_WORKER_PASSWORD" not in present:
        with ENV_FILE.open("a", encoding="utf-8") as config:
            for key in ("LOCAL_REDIS_PASSWORD", "LOCAL_WORKER_PASSWORD"):
                if key not in present:
                    config.write(f"{key}={secrets.token_hex(32)}\n")
    values = load_env()
    compose("up", "-d", "--wait", "db")
    with admin_connection() as conn:
        for role, password in [
            ("supabase_auth_admin", values["LOCAL_AUTH_PASSWORD"]),
            ("app_api", values["LOCAL_APP_PASSWORD"]),
            ("app_worker", values["LOCAL_WORKER_PASSWORD"]),
        ]:
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                conn.execute(
                    sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS").format(
                        sql.Identifier(role)
                    )
                )
            conn.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)
                )
            )
        conn.execute("CREATE SCHEMA IF NOT EXISTS auth AUTHORIZATION supabase_auth_admin")
        conn.execute("ALTER ROLE supabase_auth_admin SET search_path TO auth, public")
    compose("up", "-d", "auth", "redis")
    for _ in range(60):
        try:
            if httpx.get(os.environ["AUTH_URL"] + "/health", timeout=2).is_success:
                print("Local PostgreSQL, Supabase Auth and Redis ready (synthetic data only).")
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise SystemExit("Auth health check did not pass; inspect the local service.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "api", "web", "test", "migrate",
                                            "worker", "beat"])
    args, extra = parser.parse_known_args()
    if args.command == "prepare":
        prepare()
        return
    load_env()
    if args.command == "migrate":
        from scripts.migrate import migrate

        with admin_connection() as conn:
            migrate(conn)
        return
    commands = {
        "api": [
            sys.executable,
            "-m",
            "uvicorn",
            "leadflow.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        "test": [sys.executable, "-m", "pytest"],
        "web": ["npm.cmd" if os.name == "nt" else "npm", "run", "dev"],
        "worker": [sys.executable, "-m", "celery", "-A", "leadflow.recovery:celery_app",
                   "worker", "--pool=solo", "--loglevel=warning"],
        "beat": [sys.executable, "-m", "celery", "-A", "leadflow.recovery:celery_app",
                 "beat", "--loglevel=warning"],
    }
    cwd = ROOT / "apps/web" if args.command == "web" else ROOT
    raise SystemExit(subprocess.call(commands[args.command] + extra, cwd=cwd))


if __name__ == "__main__":
    main()
