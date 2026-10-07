"""Local synthetic SL-01 environment only. Never reads production credentials."""

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psycopg
from cryptography.fernet import Fernet
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ENV_FILE = ROOT / ".local" / "sl01.env"
OPENAI_ENV_FILE = ROOT / ".local" / "openai.env"
TELEGRAM_ENV_FILE = ROOT / ".local" / "telegram.env"


def load_env():
    if not ENV_FILE.exists():
        raise SystemExit("Run scripts/local.py prepare first.")
    values = dict(line.split("=", 1) for line in ENV_FILE.read_text().splitlines() if line)
    os.environ.update(values)
    if OPENAI_ENV_FILE.exists():
        for line in OPENAI_ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENAI_API_KEY="):
                key = line.partition("=")[2].strip()
                if key:
                    os.environ["OPENAI_API_KEY"] = key
    if "LOCAL_TELEGRAM_FERNET_KEY" in values:
        keys = {1: values["LOCAL_TELEGRAM_FERNET_KEY"]}
        for name, value in values.items():
            if name.startswith("LOCAL_TELEGRAM_FERNET_KEY_V"):
                keys[int(name.removeprefix("LOCAL_TELEGRAM_FERNET_KEY_V"))] = value
        os.environ["TELEGRAM_FERNET_KEYS"] = ",".join(
            f"{version}:{value}" for version, value in sorted(keys.items()))
        os.environ["TELEGRAM_FERNET_ACTIVE_VERSION"] = values.get(
            "LOCAL_TELEGRAM_ACTIVE_KEY_VERSION", "1")
    if TELEGRAM_ENV_FILE.exists():
        for line in TELEGRAM_ENV_FILE.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.lstrip("\ufeff").partition("=")
            if separator and key in {"TELEGRAM_MANAGER_USERNAME", "TELEGRAM_MANAGER_TOKEN",
                                     "TELEGRAM_MANAGER_WEBHOOK_SECRET", "TELEGRAM_PUBLIC_URL"}:
                os.environ[key] = value.strip()
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://app_api:"
        + values["LOCAL_APP_PASSWORD"]
        + "@127.0.0.1:54329/leadflow_sl01"
    )
    os.environ["AUTH_URL"] = "http://127.0.0.1:54321"
    os.environ["JWT_ISSUER"] = "http://127.0.0.1:54321/auth/v1"
    os.environ["APP_ENV"] = "local"
    os.environ.setdefault("KNOWLEDGE_STORAGE_DIR", str(ROOT / ".local" / "knowledge"))
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
    if "LOCAL_TELEGRAM_FERNET_KEY" not in present:
        with ENV_FILE.open("a", encoding="utf-8") as config:
            config.write("LOCAL_TELEGRAM_FERNET_KEY=" + Fernet.generate_key().decode() + "\n")
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
                                            "worker", "beat", "telegram-webhook",
                                            "telegram-rotate-key", "tunnel"])
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
    if args.command == "telegram-rotate-key":
        sys.path.insert(0, str(ROOT / "apps/api/src"))
        from leadflow.telegram import decrypt_secret, encrypt_secret

        values = load_env()
        versions = [1] + [int(name.removeprefix("LOCAL_TELEGRAM_FERNET_KEY_V"))
                          for name in values if name.startswith("LOCAL_TELEGRAM_FERNET_KEY_V")]
        new_version = max(versions) + 1
        with ENV_FILE.open("a", encoding="utf-8") as config:
            config.write(f"LOCAL_TELEGRAM_FERNET_KEY_V{new_version}="
                         + Fernet.generate_key().decode() + "\n")
            config.write(f"LOCAL_TELEGRAM_ACTIVE_KEY_VERSION={new_version}\n")
        load_env()
        with admin_connection() as conn:
            rows = conn.execute("""SELECT organization_id, request_ciphertext,
                token_ciphertext, webhook_secret_ciphertext
                FROM app.telegram_provisioning FOR UPDATE""").fetchall()
            for org, request, token, webhook in rows:
                conn.execute("""UPDATE app.telegram_provisioning
                    SET request_ciphertext = %s, token_ciphertext = %s,
                        webhook_secret_ciphertext = %s WHERE organization_id = %s""",
                    (encrypt_secret(decrypt_secret(request)),
                     encrypt_secret(decrypt_secret(token)) if token else None,
                     encrypt_secret(decrypt_secret(webhook)) if webhook else None, org))
        print(f"Telegram secrets re-encrypted with key version {new_version}; "
              "restart the API before onboarding.")
        return
    if args.command == "telegram-webhook":
        sys.path.insert(0, str(ROOT / "apps/api/src"))
        from leadflow.telegram import bot_api

        token = os.environ.get("TELEGRAM_MANAGER_TOKEN", "")
        username = os.environ.get("TELEGRAM_MANAGER_USERNAME", "").lstrip("@")
        base = os.environ.get("TELEGRAM_PUBLIC_URL", "").rstrip("/")
        if not token or not username or not base.startswith("https://"):
            raise SystemExit("Configure manager username/token and public HTTPS URL locally.")
        secret = os.environ.get("TELEGRAM_MANAGER_WEBHOOK_SECRET", "")
        if not secret:
            secret = secrets.token_urlsafe(32)
            with TELEGRAM_ENV_FILE.open("a", encoding="utf-8") as config:
                config.write("TELEGRAM_MANAGER_WEBHOOK_SECRET=" + secret + "\n")
        identity = bot_api(token, "getMe", {})
        if not isinstance(identity, dict) or identity.get("username", "").lower() != username.lower():
            raise SystemExit("Manager bot identity does not match the configured username.")
        url = base + "/v1/telegram/manager/updates"
        bot_api(token, "setWebhook", {"url": url, "secret_token": secret,
                                      "allowed_updates": ["message", "managed_bot"]})
        info = bot_api(token, "getWebhookInfo", {})
        if not isinstance(info, dict) or info.get("url") != url:
            raise SystemExit("Telegram did not confirm the manager webhook.")
        print("Manager webhook confirmed for @" + username + ".")
        return
    if args.command == "tunnel":
        # The tunnel must serve exactly the host registered in the Telegram webhooks.
        base = os.environ.get("TELEGRAM_PUBLIC_URL", "").rstrip("/")
        if not base.startswith("https://") or "/" in base.removeprefix("https://"):
            raise SystemExit("Set TELEGRAM_PUBLIC_URL to https://<static ngrok domain> first.")
        # Terminals opened before a winget install keep the old PATH, so also look where winget puts it.
        winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet"
        candidates = [shutil.which("ngrok"), winget / "Links" / "ngrok.exe",
                      *(winget / "Packages").glob("Ngrok.Ngrok_*/ngrok.exe")]
        ngrok = next((str(path) for path in candidates if path and Path(path).is_file()), None)
        if ngrok is None:
            raise SystemExit("ngrok not found; install it with: winget install --id Ngrok.Ngrok, "
                             "then run: ngrok update")
        raise SystemExit(subprocess.call([ngrok, "http", "--url=" + base, "8000"] + extra, cwd=ROOT))
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
