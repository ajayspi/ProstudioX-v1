"""
ProstudioX — Supabase client (keys via Vault, video metadata, Storage).

Security model:
  - API keys (Pexels/OpenAI/Gemini/...) live in Supabase **Vault**, encrypted.
  - This client reads them through a `security definer` RPC (`get_secret`).
  - Only the **service_role** key can call it; that key lives in env vars and
    is NEVER committed to the repo.

Env vars required (set them, don't hardcode):
  SUPABASE_URL             https://<project>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY   (the secret one, NOT the anon key)

Usage:
    from modules.supabase_client import SupabaseClient
    sb = SupabaseClient()
    pexels = sb.get_secret("PEXELS_API_KEY")
    sb.upload_video("out/video.mp4", "2026-08-22/topic.mp4")
    sb.insert_video({"topic": "...", "title": "...", "storage_path": "..."})
"""

import os

try:
    from supabase import create_client, Client
except ImportError:  # pragma: no cover
    create_client = None
    Client = None


class SupabaseClient:
    def __init__(self, url: str = None, service_role_key: str = None,
                 bucket: str = "videos"):
        self.url = url or os.getenv("SUPABASE_URL")
        self.service_role_key = (service_role_key
                                 or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                                 or os.getenv("SUPABASE_SERVICE_KEY"))
        self.bucket = bucket

        if not self.url or not self.service_role_key:
            raise RuntimeError(
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars "
                "(the service_role key, never the anon key)."
            )
        if create_client is None:
            raise RuntimeError("supabase not installed. Run: pip install supabase")

        self.client: Client = create_client(self.url, self.service_role_key)

    # ---------------------------------------------------------------- #
    #  Secrets (Vault)                                                 #
    # ---------------------------------------------------------------- #

    def get_secret(self, name: str) -> str:
        """Read one secret from Supabase Vault via the get_secret RPC."""
        res = self.client.rpc("get_secret", {"secret_name": name}).execute()
        if not res.data:
            raise KeyError(f"Secret '{name}' not found in Vault")
        row = res.data[0] if isinstance(res.data, list) else res.data
        # column name depends on the RPC return shape (see schema.sql)
        return row.get("secret_value") or row.get("decrypted_secret") or ""

    def get_secrets(self, *names: str) -> dict:
        return {n: self.get_secret(n) for n in names}

    # ---------------------------------------------------------------- #
    #  Storage                                                         #
    # ---------------------------------------------------------------- #

    def upload_video(self, local_path: str, storage_path: str,
                     content_type: str = "video/mp4") -> str:
        """Upload a finished video to the storage bucket; returns public path."""
        with open(local_path, "rb") as f:
            self.client.storage.from_(self.bucket).upload(
                path=storage_path, file=f,
                file_options={"content-type": content_type, "upsert": "true"},
            )
        return self.client.storage.from_(self.bucket).get_public_url(storage_path)

    # ---------------------------------------------------------------- #
    #  Database                                                        #
    # ---------------------------------------------------------------- #

    def insert_video(self, metadata: dict) -> dict:
        """Insert one row into the `videos` table. Returns inserted record."""
        res = self.client.table("videos").insert(metadata).execute()
        return res.data[0] if res.data else {}

    def update_video(self, video_id: str, patch: dict) -> dict:
        res = self.client.table("videos").update(patch).eq("id", video_id).execute()
        return res.data[0] if res.data else {}

    def list_videos(self, limit: int = 50):
        res = self.client.table("videos").select("*").order(
            "created_at", desc=True).limit(limit).execute()
        return res.data or []
